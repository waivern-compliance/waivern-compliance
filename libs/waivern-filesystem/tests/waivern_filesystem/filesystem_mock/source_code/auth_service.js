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
 */

import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';
import rateLimit from 'express-rate-limit';
import { User, LoginAttempt, Session } from '../models/index.js';
import { EmailService } from '../services/EmailService.js';
import { AuditLogger } from '../services/AuditLogger.js';
import { EncryptionService } from '../services/EncryptionService.js';

class AuthService {
    constructor() {
        this.emailService = new EmailService();
        this.auditLogger = new AuditLogger();
        this.encryptionService = new EncryptionService();

        // Rate limiting for login attempts
        this.loginLimiter = rateLimit({
            windowMs: 15 * 60 * 1000, // 15 minutes
            max: 5, // limit each IP to 5 requests per windowMs
            message: 'Too many login attempts, please try again later',
            standardHeaders: true,
            legacyHeaders: false,
        });
    }

    /**
     * User registration - collects personal data
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

        // Log personal data collection
        await this.auditLogger.logPersonalDataCollection({
            userId: user.id,
            action: 'user_registration',
            dataTypes: ['email', 'name', 'phone', 'date_of_birth'],
            legalBasis: 'consent',
            consentGiven: true,
            ipAddress: userData.ipAddress,
            userAgent: userData.userAgent,
            timestamp: new Date()
        });

        // Send verification email (contains personal data)
        await this.emailService.sendVerificationEmail(user.email, user.firstName);

        return {
            userId: user.id,
            email: user.email,
            message: 'Registration successful. Please check your email for verification.'
        };
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

            // Log successful authentication
            await this.auditLogger.logPersonalDataAccess({
                userId: user.id,
                action: 'user_login',
                accessedFields: ['email', 'firstName', 'lastName'],
                ipAddress: ipAddress,
                sessionId: session.id,
                timestamp: new Date()
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

                // Log session termination
                await this.auditLogger.logSessionEnd({
                    userId: decoded.userId,
                    sessionId: session.id,
                    terminatedAt: new Date(),
                    reason: 'user_logout'
                });
            }

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

            // Send reset email (contains personal data)
            await this.emailService.sendPasswordResetEmail(user.email, user.firstName, resetToken);

            // Log password reset request
            await this.auditLogger.logPersonalDataAccess({
                userId: user.id,
                action: 'password_reset_request',
                ipAddress: ipAddress,
                timestamp: new Date()
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

            // Log password change
            await this.auditLogger.logPasswordChange({
                userId: user.id,
                email: user.email,
                changedAt: new Date(),
                method: 'reset_token'
            });

            // Send confirmation email
            await this.emailService.sendPasswordChangeConfirmation(user.email, user.firstName);

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
            attributes: ['id', 'email', 'firstName', 'lastName', 'phone', 'dateOfBirth', 'createdAt', 'lastLoginAt']
        });

        if (!user) {
            throw new Error('User not found');
        }

        // Decrypt sensitive fields
        const phone = user.phone ? this.encryptionService.decrypt(user.phone) : null;
        const dateOfBirth = user.dateOfBirth ? this.encryptionService.decrypt(user.dateOfBirth) : null;

        // Log profile access
        await this.auditLogger.logPersonalDataAccess({
            userId: userId,
            action: 'profile_view',
            accessedFields: ['email', 'firstName', 'lastName', 'phone', 'dateOfBirth'],
            timestamp: new Date()
        });

        return {
            id: user.id,
            email: user.email,
            firstName: user.firstName,
            lastName: user.lastName,
            phone: phone,
            dateOfBirth: dateOfBirth,
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

        // Log personal data modification
        await this.auditLogger.logPersonalDataModification({
            userId: userId,
            modifiedFields: Object.keys(updateData),
            originalData: user.dataValues,
            newData: updates,
            timestamp: new Date()
        });

        return { message: 'Profile updated successfully' };
    }

    /**
     * Delete user account - handles personal data deletion
     */
    async deleteUserAccount(userId) {
        const user = await User.findByPk(userId);

        if (!user) {
            throw new Error('User not found');
        }

        // Log data deletion before removing
        await this.auditLogger.logPersonalDataDeletion({
            userId: userId,
            email: user.email,
            deletedAt: new Date(),
            retentionPeriod: 'immediate',
            deletionReason: 'user_request'
        });

        // Anonymize user data instead of hard delete
        await user.update({
            email: `deleted_user_${userId}@anonymized.local`,
            firstName: 'DELETED',
            lastName: 'USER',
            phone: null,
            dateOfBirth: null,
            passwordResetToken: null,
            deletedAt: new Date()
        });

        // Invalidate all sessions
        await Session.update(
            { invalidatedAt: new Date() },
            { where: { userId: userId } }
        );

        return { message: 'Account deleted successfully' };
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

IP addresses (not personal data):
- 192.168.1.1
- 127.0.0.1

Session tokens (not personal data):
- eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

Database field references:
- user.email
- user.firstName + ' ' + user.lastName
- user.phone
*/
