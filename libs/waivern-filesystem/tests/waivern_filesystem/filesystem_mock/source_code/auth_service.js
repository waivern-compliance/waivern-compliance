/**
 * Authentication Service - User authentication and session management
 *
 * Handles personal data including:
 * - Email addresses for login
 * - Password hashing and validation
 * - Session tokens and user identification
 * - Login attempt tracking and security
 *
 * GDPR Compliance:
 * - Logs personal data access
 * - Implements session management
 * - Provides data retention controls
 *
 * Third-Party Service Integrations:
 * - Auth0: Federated identity management and SSO
 * - Mixpanel: User analytics and event tracking
 * - Cloudinary: Profile picture and media processing
 * - Slack: Security alert notifications
 * - Facebook Login: Social authentication
 * - LinkedIn OAuth: Professional identity verification
 * - Intercom: Customer support chat
 */

import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';
import rateLimit from 'express-rate-limit';
import { User, LoginAttempt, Session } from '../models/index.js';
import { EncryptionService } from '../services/EncryptionService.js';

// Third-party service integrations
import { ManagementClient as Auth0ManagementClient } from 'auth0';
import { AuthenticationClient as Auth0AuthClient } from 'auth0';
import Mixpanel from 'mixpanel';
import { v2 as cloudinary } from 'cloudinary';
import { WebClient as SlackClient } from '@slack/web-api';
import { IntercomClient } from 'intercom-client';

class AuthService {
    constructor() {
        this.encryptionService = new EncryptionService();

        // Rate limiting for login attempts
        this.loginLimiter = rateLimit({
            windowMs: 15 * 60 * 1000, // 15 minutes
            max: 5, // limit each IP to 5 requests per windowMs
            message: 'Too many login attempts, please try again later',
            standardHeaders: true,
            legacyHeaders: false,
        });

        // Initialise Auth0 management client for user synchronisation
        this.auth0Management = new Auth0ManagementClient({
            domain: process.env.AUTH0_DOMAIN,
            clientId: process.env.AUTH0_CLIENT_ID,
            clientSecret: process.env.AUTH0_CLIENT_SECRET,
            scope: 'read:users update:users create:users delete:users',
        });

        // Initialise Auth0 authentication client for token validation
        this.auth0Auth = new Auth0AuthClient({
            domain: process.env.AUTH0_DOMAIN,
            clientId: process.env.AUTH0_CLIENT_ID,
        });

        // Initialise Mixpanel for user analytics tracking
        this.mixpanel = Mixpanel.init(process.env.MIXPANEL_TOKEN, {
            protocol: 'https',
        });

        // Configure Cloudinary for profile image processing
        cloudinary.config({
            cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
            api_key: process.env.CLOUDINARY_API_KEY,
            api_secret: process.env.CLOUDINARY_API_SECRET,
            secure: true,
        });

        // Initialise Slack client for security notifications
        this.slackClient = new SlackClient(process.env.SLACK_BOT_TOKEN);
        this.slackSecurityChannel = process.env.SLACK_SECURITY_CHANNEL || '#security-alerts';

        // Initialise Intercom for customer support integration
        this.intercomClient = new IntercomClient({
            tokenAuth: { token: process.env.INTERCOM_ACCESS_TOKEN },
        });
    }

    /**
     * User registration - collects personal data
     *
     * Data flows to third-party services:
     * - Auth0: Creates federated identity (email, name)
     * - Mixpanel: Tracks signup event and user profile
     * - Intercom: Creates support contact record
     */
    async registerUser(userData) {
        const { email, password, firstName, lastName, phone, dateOfBirth, gdprConsent } = userData;

        // Validate required personal data
        if (!email || !this.validateEmail(email)) {
            throw new Error('Valid email address is required');
        }

        if (!password || password.length < 8) {
            throw new Error('Password must be at least 8 characters long');
        }

        if (!firstName || !lastName) {
            throw new Error('First name and last name are required');
        }

        if (!gdprConsent) {
            throw new Error('GDPR consent is required for registration');
        }

        // Check if user already exists
        const existingUser = await User.findOne({
            where: { email: email.toLowerCase() }
        });

        if (existingUser) {
            throw new Error('User with this email already exists');
        }

        // Hash password
        const hashedPassword = await bcrypt.hash(password, 12);

        // Encrypt sensitive personal data
        const encryptedPhone = phone ? this.encryptionService.encrypt(phone) : null;
        const encryptedDateOfBirth = dateOfBirth ? this.encryptionService.encrypt(dateOfBirth) : null;

        // Create user record
        const user = await User.create({
            email: email.toLowerCase(),
            password: hashedPassword,
            firstName: firstName,
            lastName: lastName,
            phone: encryptedPhone,
            dateOfBirth: encryptedDateOfBirth,
            gdprConsentGivenAt: new Date(),
            emailVerified: false,
            createdAt: new Date()
        });

        // Create Auth0 federated identity (shares personal data: email, name)
        try {
            const auth0User = await this.auth0Management.users.create({
                connection: 'Username-Password-Authentication',
                email: email.toLowerCase(),
                given_name: firstName,
                family_name: lastName,
                name: `${firstName} ${lastName}`,
                password: password,
                email_verified: false,
                app_metadata: {
                    internal_user_id: user.id,
                    registration_source: 'direct',
                },
                user_metadata: {
                    gdpr_consent: true,
                    consent_date: new Date().toISOString(),
                },
            });

            await user.update({ auth0UserId: auth0User.user_id });
        } catch (auth0Error) {
            console.error('Auth0 user creation failed:', auth0Error.message);
            // Continue - local account still created
        }

        // Track signup in Mixpanel analytics (personal data: user traits)
        this.mixpanel.people.set(user.id.toString(), {
            '$email': email.toLowerCase(),
            '$first_name': firstName,
            '$last_name': lastName,
            '$created': new Date().toISOString(),
            'registration_method': 'email',
            'has_phone': !!phone,
            'gdpr_consent': true,
        });

        this.mixpanel.track('User Registered', {
            distinct_id: user.id.toString(),
            registration_method: 'email',
            has_phone: !!phone,
        });

        // Create Intercom contact for customer support (shares name, email)
        try {
            await this.intercomClient.contacts.createUser({
                external_id: user.id.toString(),
                email: email.toLowerCase(),
                name: `${firstName} ${lastName}`,
                signed_up_at: Math.floor(Date.now() / 1000),
                custom_attributes: {
                    registration_source: 'direct',
                    gdpr_consent: true,
                },
            });
        } catch (intercomError) {
            console.error('Intercom contact creation failed:', intercomError.message);
        }

        return {
            userId: user.id,
            email: user.email,
            message: 'Registration successful. Please check your email for verification.'
        };
    }

    /**
     * Social login via Facebook OAuth
     *
     * Receives personal data from Facebook:
     * - Facebook profile ID
     * - Email address
     * - Display name and profile picture URL
     *
     * Data processor relationship: Facebook provides identity data
     */
    async loginWithFacebook(facebookAccessToken, ipAddress, userAgent) {
        // Exchange Facebook token for user profile data
        const fbProfileResponse = await fetch(
            `https://graph.facebook.com/me?fields=id,name,email,picture&access_token=${facebookAccessToken}`
        );
        const fbProfile = await fbProfileResponse.json();

        if (!fbProfile.email) {
            throw new Error('Email permission is required for Facebook login');
        }

        // Find or create user from Facebook profile
        let user = await User.findOne({
            where: { email: fbProfile.email.toLowerCase() }
        });

        if (!user) {
            user = await User.create({
                email: fbProfile.email.toLowerCase(),
                firstName: fbProfile.name.split(' ')[0],
                lastName: fbProfile.name.split(' ').slice(1).join(' ') || '',
                password: await bcrypt.hash(require('crypto').randomBytes(32).toString('hex'), 12),
                facebookId: fbProfile.id,
                profilePictureUrl: fbProfile.picture?.data?.url,
                emailVerified: true,
                gdprConsentGivenAt: new Date(),
                createdAt: new Date()
            });

            // Upload Facebook profile picture to Cloudinary for processing
            if (fbProfile.picture?.data?.url) {
                await this.uploadProfilePicture(user.id, fbProfile.picture.data.url);
            }
        } else {
            await user.update({
                facebookId: fbProfile.id,
                lastLoginAt: new Date()
            });
        }

        // Track Facebook login in Mixpanel
        this.mixpanel.track('Social Login', {
            distinct_id: user.id.toString(),
            provider: 'facebook',
            is_new_user: !user.lastLoginAt,
        });

        // Generate session token
        const sessionToken = jwt.sign(
            { userId: user.id, email: user.email, firstName: user.firstName },
            process.env.JWT_SECRET,
            { expiresIn: '24h' }
        );

        return {
            success: true,
            token: sessionToken,
            user: {
                id: user.id,
                email: user.email,
                firstName: user.firstName,
                lastName: user.lastName,
                profilePicture: user.profilePictureUrl,
            },
            loginMethod: 'facebook',
        };
    }

    /**
     * Social login via LinkedIn OAuth
     *
     * Receives professional identity data from LinkedIn:
     * - LinkedIn member ID
     * - Email, first name, last name
     * - Profile picture URL
     * - Professional headline
     *
     * Data processor relationship: LinkedIn provides professional identity data
     */
    async loginWithLinkedIn(linkedinAuthCode, redirectUri, ipAddress) {
        // Exchange authorization code for LinkedIn access token
        const tokenResponse = await fetch('https://www.linkedin.com/oauth/v2/accessToken', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({
                grant_type: 'authorization_code',
                code: linkedinAuthCode,
                redirect_uri: redirectUri,
                client_id: process.env.LINKEDIN_CLIENT_ID,
                client_secret: process.env.LINKEDIN_CLIENT_SECRET,
            }),
        });
        const tokenData = await tokenResponse.json();

        // Fetch LinkedIn profile (personal data: name, email, photo)
        const profileResponse = await fetch('https://api.linkedin.com/v2/userinfo', {
            headers: { Authorization: `Bearer ${tokenData.access_token}` },
        });
        const linkedinProfile = await profileResponse.json();

        // Find or create user from LinkedIn profile
        let user = await User.findOne({
            where: { email: linkedinProfile.email.toLowerCase() }
        });

        if (!user) {
            user = await User.create({
                email: linkedinProfile.email.toLowerCase(),
                firstName: linkedinProfile.given_name,
                lastName: linkedinProfile.family_name,
                password: await bcrypt.hash(require('crypto').randomBytes(32).toString('hex'), 12),
                linkedinId: linkedinProfile.sub,
                emailVerified: linkedinProfile.email_verified || false,
                gdprConsentGivenAt: new Date(),
                createdAt: new Date()
            });
        }

        // Track LinkedIn login in Mixpanel
        this.mixpanel.track('Social Login', {
            distinct_id: user.id.toString(),
            provider: 'linkedin',
            is_new_user: !user.lastLoginAt,
        });

        const sessionToken = jwt.sign(
            { userId: user.id, email: user.email, firstName: user.firstName },
            process.env.JWT_SECRET,
            { expiresIn: '24h' }
        );

        return {
            success: true,
            token: sessionToken,
            user: {
                id: user.id,
                email: user.email,
                firstName: user.firstName,
                lastName: user.lastName,
            },
            loginMethod: 'linkedin',
        };
    }

    /**
     * Upload and process profile picture via Cloudinary
     *
     * Cloudinary receives the user's profile image (biometric-adjacent data).
     * Images are transformed and stored on Cloudinary's CDN.
     */
    async uploadProfilePicture(userId, imageSource) {
        try {
            const result = await cloudinary.uploader.upload(imageSource, {
                folder: `users/${userId}/profile`,
                public_id: `avatar_${userId}`,
                overwrite: true,
                transformation: [
                    { width: 400, height: 400, crop: 'fill', gravity: 'face' },
                    { quality: 'auto', fetch_format: 'auto' },
                ],
                tags: [`user_${userId}`, 'profile_picture'],
            });

            // Update user record with Cloudinary URL
            const user = await User.findByPk(userId);
            if (user) {
                await user.update({
                    profilePictureUrl: result.secure_url,
                    profilePicturePublicId: result.public_id,
                });
            }

            return {
                url: result.secure_url,
                publicId: result.public_id,
                width: result.width,
                height: result.height,
            };
        } catch (error) {
            console.error('Cloudinary upload failed:', error.message);
            throw new Error('Profile picture upload failed');
        }
    }

    /**
     * Delete profile picture from Cloudinary
     */
    async deleteProfilePicture(userId) {
        const user = await User.findByPk(userId);
        if (user?.profilePicturePublicId) {
            await cloudinary.uploader.destroy(user.profilePicturePublicId);
            await user.update({
                profilePictureUrl: null,
                profilePicturePublicId: null,
            });
        }
    }

    /**
     * User login - processes email and password
     */
    async loginUser(email, password, ipAddress, userAgent) {
        const loginAttempt = {
            email: email.toLowerCase(),
            ipAddress: ipAddress,
            userAgent: userAgent,
            timestamp: new Date(),
            success: false
        };

        try {
            // Validate email format
            if (!email || !this.validateEmail(email)) {
                throw new Error('Invalid email format');
            }

            // Find user by email (personal data lookup)
            const user = await User.findOne({
                where: {
                    email: email.toLowerCase(),
                    deletedAt: null
                }
            });

            if (!user) {
                throw new Error('Invalid credentials');
            }

            // Verify password
            const passwordValid = await bcrypt.compare(password, user.password);
            if (!passwordValid) {
                // Send security alert to Slack for repeated failures
                const recentFailures = await LoginAttempt.count({
                    where: {
                        email: email.toLowerCase(),
                        success: false,
                        timestamp: { $gte: new Date(Date.now() - 15 * 60 * 1000) }
                    }
                });

                if (recentFailures >= 3) {
                    await this.sendSlackSecurityAlert(
                        'Repeated Login Failures',
                        `Multiple failed login attempts for ${email} from IP ${ipAddress}. ` +
                        `${recentFailures + 1} failures in the last 15 minutes.`
                    );
                }

                throw new Error('Invalid credentials');
            }

            // Check if email is verified
            if (!user.emailVerified) {
                throw new Error('Please verify your email address before logging in');
            }

            // Generate session token
            const sessionToken = jwt.sign(
                {
                    userId: user.id,
                    email: user.email,
                    firstName: user.firstName
                },
                process.env.JWT_SECRET,
                { expiresIn: '24h' }
            );

            // Create session record
            const session = await Session.create({
                userId: user.id,
                sessionToken: sessionToken,
                ipAddress: ipAddress,
                userAgent: userAgent,
                expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000), // 24 hours
                createdAt: new Date()
            });

            // Update user's last login
            await user.update({
                lastLoginAt: new Date(),
                lastLoginIp: ipAddress
            });

            loginAttempt.success = true;
            loginAttempt.userId = user.id;
            loginAttempt.sessionId = session.id;

            // Track login event in Mixpanel
            this.mixpanel.track('User Login', {
                distinct_id: user.id.toString(),
                login_method: 'email',
                ip_address: ipAddress,
            });

            this.mixpanel.people.set(user.id.toString(), {
                '$last_login': new Date().toISOString(),
                'last_login_ip': ipAddress,
            });

            return {
                success: true,
                token: sessionToken,
                user: {
                    id: user.id,
                    email: user.email,
                    firstName: user.firstName,
                    lastName: user.lastName
                }
            };

        } catch (error) {
            loginAttempt.error = error.message;
            throw error;
        } finally {
            // Log login attempt (contains personal data - email)
            await LoginAttempt.create(loginAttempt);
        }
    }

    /**
     * Logout user - invalidate session
     */
    async logoutUser(sessionToken) {
        try {
            const decoded = jwt.verify(sessionToken, process.env.JWT_SECRET);

            // Find and invalidate session
            const session = await Session.findOne({
                where: {
                    userId: decoded.userId,
                    sessionToken: sessionToken,
                    invalidatedAt: null
                }
            });

            if (session) {
                await session.update({
                    invalidatedAt: new Date()
                });
            }

            // Track logout in Mixpanel
            this.mixpanel.track('User Logout', {
                distinct_id: decoded.userId.toString(),
            });

            return { success: true, message: 'Logged out successfully' };
        } catch (error) {
            throw new Error('Invalid session token');
        }
    }

    /**
     * Verify session token - accesses personal data
     */
    async verifySession(sessionToken) {
        try {
            const decoded = jwt.verify(sessionToken, process.env.JWT_SECRET);

            // Check if session exists and is valid
            const session = await Session.findOne({
                where: {
                    userId: decoded.userId,
                    sessionToken: sessionToken,
                    invalidatedAt: null
                },
                include: [{
                    model: User,
                    attributes: ['id', 'email', 'firstName', 'lastName', 'deletedAt']
                }]
            });

            if (!session || session.expiresAt < new Date() || session.User.deletedAt) {
                throw new Error('Invalid or expired session');
            }

            // Update last activity
            await session.update({
                lastActivityAt: new Date()
            });

            return {
                valid: true,
                user: {
                    id: session.User.id,
                    email: session.User.email,
                    firstName: session.User.firstName,
                    lastName: session.User.lastName
                }
            };
        } catch (error) {
            return { valid: false, error: error.message };
        }
    }

    /**
     * Password reset request - processes email address
     */
    async requestPasswordReset(email, ipAddress) {
        if (!email || !this.validateEmail(email)) {
            throw new Error('Valid email address is required');
        }

        const user = await User.findOne({
            where: { email: email.toLowerCase() }
        });

        // Always respond with success to prevent email enumeration
        // but only send email if user exists
        if (user) {
            // Generate reset token
            const resetToken = jwt.sign(
                { userId: user.id, email: user.email, purpose: 'password_reset' },
                process.env.JWT_SECRET,
                { expiresIn: '1h' }
            );

            // Store reset token
            await user.update({
                passwordResetToken: resetToken,
                passwordResetExpiresAt: new Date(Date.now() + 60 * 60 * 1000) // 1 hour
            });

            // Track password reset request in Mixpanel
            this.mixpanel.track('Password Reset Requested', {
                distinct_id: user.id.toString(),
                ip_address: ipAddress,
            });
        }

        return { message: 'If the email exists in our system, a password reset link has been sent.' };
    }

    /**
     * Reset password using token
     */
    async resetPassword(resetToken, newPassword) {
        try {
            const decoded = jwt.verify(resetToken, process.env.JWT_SECRET);

            if (decoded.purpose !== 'password_reset') {
                throw new Error('Invalid reset token');
            }

            const user = await User.findOne({
                where: {
                    id: decoded.userId,
                    email: decoded.email,
                    passwordResetToken: resetToken
                }
            });

            if (!user || user.passwordResetExpiresAt < new Date()) {
                throw new Error('Invalid or expired reset token');
            }

            // Hash new password
            const hashedPassword = await bcrypt.hash(newPassword, 12);

            // Update password and clear reset token
            await user.update({
                password: hashedPassword,
                passwordResetToken: null,
                passwordResetExpiresAt: null,
                passwordChangedAt: new Date()
            });

            // Invalidate all existing sessions for security
            await Session.update(
                { invalidatedAt: new Date() },
                { where: { userId: user.id, invalidatedAt: null } }
            );

            // Send Slack security notification for password change
            await this.sendSlackSecurityAlert(
                'Password Changed',
                `User ${user.email} successfully reset their password via reset token.`
            );

            // Track password change in Mixpanel
            this.mixpanel.track('Password Reset Completed', {
                distinct_id: user.id.toString(),
                method: 'reset_token',
            });

            return { message: 'Password reset successfully' };
        } catch (error) {
            throw new Error('Invalid or expired reset token');
        }
    }

    /**
     * Get user profile - returns personal data
     */
    async getUserProfile(userId) {
        const user = await User.findByPk(userId, {
            attributes: ['id', 'email', 'firstName', 'lastName', 'phone', 'dateOfBirth', 'createdAt', 'lastLoginAt', 'profilePictureUrl']
        });

        if (!user) {
            throw new Error('User not found');
        }

        // Decrypt sensitive fields
        const phone = user.phone ? this.encryptionService.decrypt(user.phone) : null;
        const dateOfBirth = user.dateOfBirth ? this.encryptionService.decrypt(user.dateOfBirth) : null;

        return {
            id: user.id,
            email: user.email,
            firstName: user.firstName,
            lastName: user.lastName,
            phone: phone,
            dateOfBirth: dateOfBirth,
            profilePicture: user.profilePictureUrl,
            memberSince: user.createdAt,
            lastLogin: user.lastLoginAt
        };
    }

    /**
     * Update user profile - modifies personal data
     */
    async updateUserProfile(userId, updates) {
        const user = await User.findByPk(userId);

        if (!user) {
            throw new Error('User not found');
        }

        const allowedUpdates = ['firstName', 'lastName', 'phone'];
        const updateData = {};

        // Validate and prepare updates
        for (const field of allowedUpdates) {
            if (updates[field] !== undefined) {
                if (field === 'phone') {
                    updateData[field] = updates[field] ? this.encryptionService.encrypt(updates[field]) : null;
                } else {
                    updateData[field] = updates[field];
                }
            }
        }

        if (Object.keys(updateData).length === 0) {
            throw new Error('No valid updates provided');
        }

        // Update user
        await user.update(updateData);

        // Sync profile changes to Auth0 (shares updated personal data)
        if (user.auth0UserId) {
            try {
                await this.auth0Management.users.update(
                    { id: user.auth0UserId },
                    {
                        given_name: user.firstName,
                        family_name: user.lastName,
                        name: `${user.firstName} ${user.lastName}`,
                    }
                );
            } catch (auth0Error) {
                console.error('Auth0 profile sync failed:', auth0Error.message);
            }
        }

        // Update Mixpanel profile with new personal data
        this.mixpanel.people.set(userId.toString(), {
            '$first_name': user.firstName,
            '$last_name': user.lastName,
        });

        // Update Intercom contact with new personal data
        try {
            await this.intercomClient.contacts.update({
                external_id: userId.toString(),
                name: `${user.firstName} ${user.lastName}`,
            });
        } catch (intercomError) {
            console.error('Intercom contact update failed:', intercomError.message);
        }

        // Track profile update in Mixpanel
        this.mixpanel.track('Profile Updated', {
            distinct_id: userId.toString(),
            updated_fields: Object.keys(updateData),
        });

        return { message: 'Profile updated successfully' };
    }

    /**
     * Delete user account - handles personal data deletion across services
     *
     * Cleanup across third-party services:
     * - Auth0: Delete federated identity
     * - Mixpanel: Delete user profile and events
     * - Cloudinary: Remove profile pictures
     * - Intercom: Delete support contact
     */
    async deleteUserAccount(userId) {
        const user = await User.findByPk(userId);

        if (!user) {
            throw new Error('User not found');
        }

        // Delete Auth0 federated identity
        if (user.auth0UserId) {
            try {
                await this.auth0Management.users.delete({ id: user.auth0UserId });
            } catch (auth0Error) {
                console.error('Auth0 user deletion failed:', auth0Error.message);
            }
        }

        // Delete profile picture from Cloudinary
        await this.deleteProfilePicture(userId);

        // Request Mixpanel data deletion (GDPR compliance)
        this.mixpanel.people.delete_user(userId.toString());

        // Delete Intercom contact
        try {
            await this.intercomClient.contacts.delete({
                external_id: userId.toString(),
            });
        } catch (intercomError) {
            console.error('Intercom contact deletion failed:', intercomError.message);
        }

        // Anonymize user data instead of hard delete
        await user.update({
            email: `deleted_user_${userId}@anonymized.local`,
            firstName: 'DELETED',
            lastName: 'USER',
            phone: null,
            dateOfBirth: null,
            facebookId: null,
            linkedinId: null,
            auth0UserId: null,
            profilePictureUrl: null,
            passwordResetToken: null,
            deletedAt: new Date()
        });

        // Invalidate all sessions
        await Session.update(
            { invalidatedAt: new Date() },
            { where: { userId: userId } }
        );

        // Send Slack notification about account deletion
        await this.sendSlackSecurityAlert(
            'Account Deleted',
            `User account ${userId} has been deleted and personal data cleaned up ` +
            `across Auth0, Cloudinary, Mixpanel, and Intercom.`
        );

        return { message: 'Account deleted successfully' };
    }

    /**
     * Send security alert to Slack channel
     *
     * Used for security events like:
     * - Multiple failed login attempts
     * - Password changes
     * - Account deletions
     * - Suspicious activity detection
     *
     * Alert messages may reference personal data (email addresses, IP addresses).
     */
    async sendSlackSecurityAlert(title, message) {
        try {
            await this.slackClient.chat.postMessage({
                channel: this.slackSecurityChannel,
                text: `*Security Alert: ${title}*\n${message}`,
                blocks: [
                    {
                        type: 'header',
                        text: { type: 'plain_text', text: `Security Alert: ${title}` },
                    },
                    {
                        type: 'section',
                        text: { type: 'mrkdwn', text: message },
                    },
                    {
                        type: 'context',
                        elements: [
                            {
                                type: 'mrkdwn',
                                text: `*Timestamp:* ${new Date().toISOString()} | *Source:* AuthService`,
                            },
                        ],
                    },
                ],
            });
        } catch (slackError) {
            console.error('Slack security alert failed:', slackError.message);
        }
    }

    // Helper methods

    /**
     * Validate email format
     */
    validateEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    /**
     * Validate phone number (UK format)
     */
    validatePhoneNumber(phone) {
        const ukPhoneRegex = /^(\+44|0)[1-9]\d{8,9}$/;
        return ukPhoneRegex.test(phone.replace(/\s+/g, ''));
    }

    /**
     * Generate secure random token
     */
    generateSecureToken() {
        return require('crypto').randomBytes(32).toString('hex');
    }
}

export { AuthService };

// Example usage and test data patterns
/*
Test scenarios for personal data detection:

Valid emails:
- user@example.com
- john.doe@company.co.uk
- sarah.wilson@gmail.com

Phone numbers:
- +44 20 7946 0958
- 07700 900123
- +1 555 234 5678

Personal names in code:
- firstName: "John"
- lastName: "Smith"
- fullName: "Sarah Johnson"

Date of birth patterns:
- dateOfBirth: "1987-03-15"
- dob: new Date("1985-07-22")

Third-party service data flows:
- Auth0: email, name -> federated identity
- Mixpanel: user traits, events -> analytics
- Cloudinary: profile pictures -> media CDN
- Slack: security alerts (may contain emails, IPs)
- Facebook: email, name, profile picture -> social login
- LinkedIn: email, name, professional data -> social login
- Intercom: email, name -> customer support
*/
