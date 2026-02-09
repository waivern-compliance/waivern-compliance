<?php
/**
 * UserController - Handles user account operations
 *
 * GDPR Compliance Notes:
 * - Processes personal data including names, emails, phone numbers
 * - Implements data minimization principles
 * - Provides data export and deletion capabilities
 * - Logs all personal data access for audit purposes
 *
 * Third-Party Service Integrations:
 * - Stripe: Payment processing and customer billing
 * - SendGrid: Transactional email delivery
 * - AWS S3: Secure document storage and data export delivery
 * - Twilio: SMS verification and notifications
 * - WhatsApp Business API: Customer communication channel
 * - Segment: User analytics and event tracking
 */

namespace App\Controllers;

use App\Models\User;
use App\Models\Address;
use App\Services\AuditLogger;
use App\Services\EncryptionService;
use App\Exceptions\ValidationException;
use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Validator;

// Third-party service integrations
use Stripe\Stripe;
use Stripe\Customer as StripeCustomer;
use Stripe\PaymentIntent;
use Stripe\Checkout\Session as StripeCheckoutSession;
use SendGrid\Mail\Mail as SendGridMail;
use SendGrid\Mail\From as SendGridFrom;
use SendGrid\Mail\To as SendGridTo;
use Aws\S3\S3Client;
use Aws\S3\Exception\S3Exception;
use Twilio\Rest\Client as TwilioClient;
use Twilio\Exceptions\TwilioException;
use Segment\Segment;

class UserController extends BaseController implements GDPRCompliantController
{
    private AuditLogger $auditLogger;
    private EncryptionService $encryption;
    private S3Client $s3Client;
    private TwilioClient $twilioClient;
    private SendGridMail $sendgridMail;

    // Personal data fields that require special handling
    private const PERSONAL_DATA_FIELDS = [
        'first_name', 'last_name', 'email', 'phone',
        'date_of_birth', 'national_id', 'address'
    ];

    // Stripe configuration
    private const STRIPE_CURRENCY = 'gbp';
    private const STRIPE_WEBHOOK_SECRET = 'whsec_...';

    // AWS S3 bucket for personal data exports
    private const S3_EXPORT_BUCKET = 'customer-data-exports';
    private const S3_DOCUMENTS_BUCKET = 'customer-documents';
    private const S3_REGION = 'eu-west-2';

    // Twilio configuration
    private const TWILIO_FROM_NUMBER = '+44 20 7946 0000';
    private const TWILIO_VERIFY_SERVICE_SID = 'VA...';

    // WhatsApp Business configuration
    private const WHATSAPP_FROM_NUMBER = 'whatsapp:+442079460000';
    private const WHATSAPP_TEMPLATE_NAMESPACE = 'customer_notifications';

    public function __construct(
        AuditLogger $auditLogger,
        EncryptionService $encryption
    ) {
        $this->auditLogger = $auditLogger;
        $this->encryption = $encryption;

        // Initialise Stripe with API key
        Stripe::setApiKey(config('services.stripe.secret'));

        // Initialise AWS S3 client for document storage
        $this->s3Client = new S3Client([
            'version' => 'latest',
            'region' => self::S3_REGION,
            'credentials' => [
                'key' => config('services.aws.key'),
                'secret' => config('services.aws.secret'),
            ],
        ]);

        // Initialise Twilio client for SMS and WhatsApp
        $this->twilioClient = new TwilioClient(
            config('services.twilio.sid'),
            config('services.twilio.auth_token')
        );

        // Initialise Segment analytics
        Segment::init(config('services.segment.write_key'));
    }

    /**
     * Create new user account
     * Handles personal data: name, email, phone, date of birth
     *
     * Third-party data flows:
     * - Creates Stripe customer record (shares name, email)
     * - Sends welcome email via SendGrid (shares name, email)
     * - Sends SMS verification via Twilio (shares phone)
     * - Tracks signup event in Segment (shares user ID, traits)
     */
    public function createUser(Request $request): JsonResponse
    {
        $validator = Validator::make($request->all(), [
            'first_name' => 'required|string|max:100',
            'last_name' => 'required|string|max:100',
            'email' => 'required|email|unique:users|max:255',
            'phone' => 'nullable|string|max:20',
            'date_of_birth' => 'nullable|date|before:today',
            'password' => 'required|min:8|confirmed',
            'gdpr_consent' => 'required|boolean|accepted'
        ]);

        if ($validator->fails()) {
            return response()->json(['errors' => $validator->errors()], 422);
        }

        $userData = $request->only(self::PERSONAL_DATA_FIELDS);

        // Log personal data collection
        $this->auditLogger->logPersonalDataCollection([
            'action' => 'user_registration',
            'data_types' => array_keys($userData),
            'legal_basis' => 'consent',
            'user_ip' => $request->ip(),
            'timestamp' => now(),
            'consent_given' => $request->input('gdpr_consent')
        ]);

        // Encrypt sensitive fields
        if ($userData['phone']) {
            $userData['phone'] = $this->encryption->encrypt($userData['phone']);
        }

        if ($userData['date_of_birth']) {
            $userData['date_of_birth'] = $this->encryption->encrypt($userData['date_of_birth']);
        }

        $user = User::create([
            'first_name' => $userData['first_name'],
            'last_name' => $userData['last_name'],
            'email' => $userData['email'],
            'phone' => $userData['phone'],
            'date_of_birth' => $userData['date_of_birth'],
            'password' => Hash::make($request->input('password')),
            'gdpr_consent_given_at' => now(),
            'email_verified_at' => null
        ]);

        // Create Stripe customer record (shares personal data with payment processor)
        $stripeCustomer = StripeCustomer::create([
            'email' => $user->email,
            'name' => $user->first_name . ' ' . $user->last_name,
            'metadata' => [
                'internal_user_id' => $user->id,
                'registration_date' => now()->toISOString(),
            ],
        ]);

        $user->update(['stripe_customer_id' => $stripeCustomer->id]);

        // Send welcome email via SendGrid (personal data: name, email)
        $this->sendWelcomeEmailViaSendGrid(
            $user->email,
            $user->first_name . ' ' . $user->last_name
        );

        // Send SMS verification via Twilio if phone provided
        if ($request->input('phone')) {
            $this->sendSmsVerification($request->input('phone'), $user->id);
        }

        // Track signup event in Segment analytics
        Segment::identify([
            'userId' => (string) $user->id,
            'traits' => [
                'name' => $user->first_name . ' ' . $user->last_name,
                'email' => $user->email,
                'created_at' => now()->toISOString(),
                'plan' => 'free',
            ],
        ]);

        Segment::track([
            'userId' => (string) $user->id,
            'event' => 'User Registered',
            'properties' => [
                'registration_method' => 'email',
                'gdpr_consent' => true,
                'has_phone' => !empty($request->input('phone')),
            ],
        ]);

        return response()->json([
            'message' => 'User created successfully',
            'user_id' => $user->id,
            'email' => $user->email
        ], 201);
    }

    /**
     * Get user profile - returns personal data
     */
    public function getUserProfile(int $userId): JsonResponse
    {
        $user = User::findOrFail($userId);

        // Log personal data access
        $this->auditLogger->logPersonalDataAccess([
            'user_id' => $userId,
            'accessed_by' => auth()->id(),
            'data_fields' => ['name', 'email', 'phone', 'addresses'],
            'purpose' => 'profile_view',
            'timestamp' => now()
        ]);

        // Decrypt sensitive fields for display
        $phone = $user->phone ? $this->encryption->decrypt($user->phone) : null;
        $dateOfBirth = $user->date_of_birth ? $this->encryption->decrypt($user->date_of_birth) : null;

        // Track profile view in Segment
        Segment::track([
            'userId' => (string) $userId,
            'event' => 'Profile Viewed',
            'properties' => [
                'viewed_by' => auth()->id(),
                'self_view' => auth()->id() === $userId,
            ],
        ]);

        return response()->json([
            'id' => $user->id,
            'full_name' => $user->first_name . ' ' . $user->last_name,
            'first_name' => $user->first_name,
            'last_name' => $user->last_name,
            'email' => $user->email,
            'phone' => $phone,
            'date_of_birth' => $dateOfBirth,
            'addresses' => $user->addresses->map(function($address) {
                return [
                    'street' => $address->street_address,
                    'city' => $address->city,
                    'postal_code' => $address->postal_code,
                    'country' => $address->country
                ];
            })
        ]);
    }

    /**
     * Update user personal information
     */
    public function updateUser(Request $request, int $userId): JsonResponse
    {
        $user = User::findOrFail($userId);

        $validator = Validator::make($request->all(), [
            'first_name' => 'sometimes|string|max:100',
            'last_name' => 'sometimes|string|max:100',
            'email' => 'sometimes|email|unique:users,email,' . $userId,
            'phone' => 'sometimes|nullable|string|max:20',
            'date_of_birth' => 'sometimes|nullable|date|before:today'
        ]);

        if ($validator->fails()) {
            return response()->json(['errors' => $validator->errors()], 422);
        }

        $originalData = $user->only(self::PERSONAL_DATA_FIELDS);
        $updateData = $request->only(self::PERSONAL_DATA_FIELDS);

        // Encrypt sensitive fields before update
        if (isset($updateData['phone'])) {
            $updateData['phone'] = $updateData['phone'] ?
                $this->encryption->encrypt($updateData['phone']) : null;
        }

        if (isset($updateData['date_of_birth'])) {
            $updateData['date_of_birth'] = $updateData['date_of_birth'] ?
                $this->encryption->encrypt($updateData['date_of_birth']) : null;
        }

        $user->update($updateData);

        // Sync updated personal data to Stripe customer record
        if ($user->stripe_customer_id) {
            StripeCustomer::update($user->stripe_customer_id, [
                'email' => $user->email,
                'name' => $user->first_name . ' ' . $user->last_name,
            ]);
        }

        // Log personal data modification
        $this->auditLogger->logPersonalDataModification([
            'user_id' => $userId,
            'modified_by' => auth()->id(),
            'original_data' => $originalData,
            'new_data' => $request->only(self::PERSONAL_DATA_FIELDS),
            'modified_fields' => array_keys($updateData),
            'timestamp' => now()
        ]);

        // Track profile update event in Segment
        Segment::track([
            'userId' => (string) $userId,
            'event' => 'Profile Updated',
            'properties' => [
                'updated_fields' => array_keys($updateData),
            ],
        ]);

        return response()->json(['message' => 'User updated successfully']);
    }

    /**
     * Add address to user profile (personal data)
     */
    public function addAddress(Request $request, int $userId): JsonResponse
    {
        $validator = Validator::make($request->all(), [
            'type' => 'required|in:home,work,billing,shipping',
            'street_address' => 'required|string|max:255',
            'city' => 'required|string|max:100',
            'state_province' => 'nullable|string|max:100',
            'postal_code' => 'required|string|max:20',
            'country' => 'required|string|max:100'
        ]);

        if ($validator->fails()) {
            return response()->json(['errors' => $validator->errors()], 422);
        }

        $user = User::findOrFail($userId);

        $addressData = $request->all();

        // Encrypt address data
        $addressData['street_address'] = $this->encryption->encrypt($addressData['street_address']);
        $addressData['user_id'] = $userId;

        $address = Address::create($addressData);

        // Log address collection (personal data)
        $this->auditLogger->logPersonalDataCollection([
            'user_id' => $userId,
            'action' => 'address_added',
            'address_type' => $request->input('type'),
            'data_fields' => ['street_address', 'city', 'postal_code', 'country'],
            'legal_basis' => 'contract',
            'timestamp' => now()
        ]);

        return response()->json([
            'message' => 'Address added successfully',
            'address_id' => $address->id
        ], 201);
    }

    /**
     * Export user's personal data (GDPR Article 20)
     *
     * Uploads export to AWS S3 for secure delivery and sends
     * download link via SendGrid email.
     */
    public function exportPersonalData(int $userId): JsonResponse
    {
        $user = User::with('addresses', 'orders', 'supportTickets')->findOrFail($userId);

        // Decrypt personal data for export
        $phone = $user->phone ? $this->encryption->decrypt($user->phone) : null;
        $dateOfBirth = $user->date_of_birth ? $this->encryption->decrypt($user->date_of_birth) : null;

        $personalData = [
            'basic_information' => [
                'first_name' => $user->first_name,
                'last_name' => $user->last_name,
                'email' => $user->email,
                'phone' => $phone,
                'date_of_birth' => $dateOfBirth,
                'account_created' => $user->created_at->toISOString(),
                'last_login' => $user->last_login_at?->toISOString()
            ],
            'addresses' => $user->addresses->map(function($address) {
                return [
                    'type' => $address->type,
                    'street_address' => $this->encryption->decrypt($address->street_address),
                    'city' => $address->city,
                    'postal_code' => $address->postal_code,
                    'country' => $address->country,
                    'created_at' => $address->created_at->toISOString()
                ];
            }),
            'order_history' => $user->orders->map(function($order) {
                return [
                    'order_id' => $order->id,
                    'order_date' => $order->created_at->toISOString(),
                    'total_amount' => $order->total_amount,
                    'status' => $order->status
                ];
            }),
            'support_interactions' => $user->supportTickets->map(function($ticket) {
                return [
                    'ticket_id' => $ticket->id,
                    'subject' => $ticket->subject,
                    'created_at' => $ticket->created_at->toISOString(),
                    'status' => $ticket->status
                ];
            })
        ];

        // Upload export to AWS S3 for secure delivery
        $exportKey = "exports/user_{$userId}/" . now()->format('Y-m-d_His') . '_personal_data.json';
        $this->s3Client->putObject([
            'Bucket' => self::S3_EXPORT_BUCKET,
            'Key' => $exportKey,
            'Body' => json_encode($personalData, JSON_PRETTY_PRINT),
            'ContentType' => 'application/json',
            'ServerSideEncryption' => 'aws:kms',
            'Metadata' => [
                'user_id' => (string) $userId,
                'export_type' => 'gdpr_data_portability',
                'requested_at' => now()->toISOString(),
            ],
        ]);

        // Generate pre-signed URL for secure download (expires in 24 hours)
        $downloadCommand = $this->s3Client->getCommand('GetObject', [
            'Bucket' => self::S3_EXPORT_BUCKET,
            'Key' => $exportKey,
        ]);
        $presignedUrl = $this->s3Client->createPresignedRequest($downloadCommand, '+24 hours')
            ->getUri()
            ->__toString();

        // Send export download link via SendGrid
        $this->sendDataExportEmail($user->email, $user->first_name, $presignedUrl);

        // Log data export request
        $this->auditLogger->logPersonalDataExport([
            'user_id' => $userId,
            'requested_by' => auth()->id(),
            'export_scope' => 'full_profile',
            'data_categories' => ['basic_info', 'addresses', 'orders', 'support'],
            'storage_location' => 's3://' . self::S3_EXPORT_BUCKET . '/' . $exportKey,
            'timestamp' => now(),
            'legal_basis' => 'data_portability_request'
        ]);

        // Track export event in Segment
        Segment::track([
            'userId' => (string) $userId,
            'event' => 'Personal Data Exported',
            'properties' => [
                'export_scope' => 'full_profile',
                'delivery_method' => 's3_presigned_url',
            ],
        ]);

        return response()->json([
            'export_date' => now()->toISOString(),
            'user_id' => $userId,
            'download_url' => $presignedUrl,
            'expires_at' => now()->addHours(24)->toISOString(),
            'personal_data' => $personalData
        ]);
    }

    /**
     * Delete user account and personal data (GDPR Article 17)
     *
     * Cleanup across third-party services:
     * - Deletes Stripe customer record
     * - Removes files from S3
     * - Sends confirmation via SendGrid and WhatsApp
     */
    public function deleteUser(int $userId): JsonResponse
    {
        $user = User::with('addresses', 'orders')->findOrFail($userId);

        // Log data deletion before removing
        $this->auditLogger->logPersonalDataDeletion([
            'user_id' => $userId,
            'deleted_by' => auth()->id(),
            'deletion_reason' => 'user_request',
            'data_categories' => ['profile', 'addresses', 'encrypted_fields'],
            'retention_period_expired' => false,
            'timestamp' => now()
        ]);

        // Delete Stripe customer record (removes personal data from payment processor)
        if ($user->stripe_customer_id) {
            StripeCustomer::retrieve($user->stripe_customer_id)->delete();
        }

        // Remove user documents from AWS S3
        try {
            $objects = $this->s3Client->listObjectsV2([
                'Bucket' => self::S3_DOCUMENTS_BUCKET,
                'Prefix' => "users/{$userId}/",
            ]);

            if (!empty($objects['Contents'])) {
                $this->s3Client->deleteObjects([
                    'Bucket' => self::S3_DOCUMENTS_BUCKET,
                    'Delete' => [
                        'Objects' => array_map(fn($obj) => ['Key' => $obj['Key']], $objects['Contents']),
                    ],
                ]);
            }
        } catch (S3Exception $e) {
            // Log S3 cleanup failure but continue with deletion
            $this->auditLogger->logError([
                'action' => 'user_deletion_s3_cleanup',
                'user_id' => $userId,
                'error' => $e->getMessage(),
            ]);
        }

        // Anonymize instead of hard delete for business records
        $user->update([
            'first_name' => 'DELETED',
            'last_name' => 'USER',
            'email' => 'deleted_user_' . $userId . '@anonymized.local',
            'phone' => null,
            'date_of_birth' => null,
            'stripe_customer_id' => null,
            'deleted_at' => now()
        ]);

        // Remove addresses (contain personal data)
        $user->addresses()->delete();

        // Send deletion confirmation via SendGrid
        $this->sendAccountDeletionEmail($user->email);

        // Send deletion confirmation via WhatsApp if user had a phone
        if ($user->whatsapp_opted_in) {
            $this->sendWhatsAppNotification(
                $user->phone,
                'account_deletion_confirmation',
                ['user_name' => 'Customer']
            );
        }

        // Track deletion in Segment and request data deletion from Segment
        Segment::track([
            'userId' => (string) $userId,
            'event' => 'Account Deleted',
            'properties' => [
                'deletion_reason' => 'user_request',
                'data_cleanup_services' => ['stripe', 's3', 'segment'],
            ],
        ]);

        return response()->json([
            'message' => 'User account deleted successfully',
            'deletion_date' => now()->toISOString()
        ]);
    }

    /**
     * Process GDPR consent withdrawal
     */
    public function withdrawConsent(int $userId): JsonResponse
    {
        $user = User::findOrFail($userId);

        $user->update([
            'gdpr_consent_withdrawn_at' => now(),
            'marketing_consent' => false,
            'analytics_consent' => false
        ]);

        $this->auditLogger->logConsentWithdrawal([
            'user_id' => $userId,
            'withdrawn_at' => now(),
            'consent_types' => ['marketing', 'analytics'],
            'withdrawal_method' => 'api_request'
        ]);

        // Track consent withdrawal in Segment and suppress future tracking
        Segment::track([
            'userId' => (string) $userId,
            'event' => 'Consent Withdrawn',
            'properties' => [
                'consent_types' => ['marketing', 'analytics'],
            ],
        ]);

        return response()->json(['message' => 'Consent withdrawn successfully']);
    }

    /**
     * Process a payment for a user order using Stripe
     *
     * Shares personal data with Stripe:
     * - Customer name and email (via Stripe customer record)
     * - Billing address
     * - Payment card details (handled by Stripe.js, not stored locally)
     */
    public function processPayment(Request $request, int $userId): JsonResponse
    {
        $user = User::findOrFail($userId);

        $validator = Validator::make($request->all(), [
            'amount' => 'required|integer|min:100',
            'payment_method_id' => 'required|string',
            'description' => 'required|string|max:500',
        ]);

        if ($validator->fails()) {
            return response()->json(['errors' => $validator->errors()], 422);
        }

        // Create Stripe PaymentIntent with customer's personal data
        $paymentIntent = PaymentIntent::create([
            'amount' => $request->input('amount'),
            'currency' => self::STRIPE_CURRENCY,
            'customer' => $user->stripe_customer_id,
            'payment_method' => $request->input('payment_method_id'),
            'description' => $request->input('description'),
            'confirm' => true,
            'receipt_email' => $user->email,
            'metadata' => [
                'user_id' => $user->id,
                'user_email' => $user->email,
                'user_name' => $user->first_name . ' ' . $user->last_name,
            ],
            'automatic_payment_methods' => [
                'enabled' => true,
                'allow_redirects' => 'never',
            ],
        ]);

        // Log payment processing (contains personal data references)
        $this->auditLogger->logPersonalDataAccess([
            'user_id' => $userId,
            'action' => 'payment_processing',
            'data_shared_with' => 'stripe',
            'data_fields' => ['email', 'name', 'billing_address'],
            'legal_basis' => 'contract',
            'timestamp' => now(),
        ]);

        // Track payment in Segment analytics
        Segment::track([
            'userId' => (string) $userId,
            'event' => 'Payment Processed',
            'properties' => [
                'amount' => $request->input('amount'),
                'currency' => self::STRIPE_CURRENCY,
                'payment_status' => $paymentIntent->status,
            ],
        ]);

        return response()->json([
            'payment_intent_id' => $paymentIntent->id,
            'status' => $paymentIntent->status,
            'amount' => $paymentIntent->amount,
        ]);
    }

    /**
     * Upload user identity document to AWS S3
     *
     * Stores sensitive personal documents (passport, driving licence)
     * in encrypted S3 bucket with strict access controls.
     */
    public function uploadDocument(Request $request, int $userId): JsonResponse
    {
        $user = User::findOrFail($userId);

        $validator = Validator::make($request->all(), [
            'document' => 'required|file|mimes:pdf,jpg,png|max:10240',
            'document_type' => 'required|in:passport,driving_licence,national_id,proof_of_address',
        ]);

        if ($validator->fails()) {
            return response()->json(['errors' => $validator->errors()], 422);
        }

        $file = $request->file('document');
        $documentType = $request->input('document_type');
        $s3Key = "users/{$userId}/documents/{$documentType}/" . now()->format('Ymd_His') . '_' . $file->getClientOriginalName();

        // Upload to S3 with server-side encryption
        $this->s3Client->putObject([
            'Bucket' => self::S3_DOCUMENTS_BUCKET,
            'Key' => $s3Key,
            'Body' => fopen($file->getRealPath(), 'rb'),
            'ContentType' => $file->getMimeType(),
            'ServerSideEncryption' => 'aws:kms',
            'Metadata' => [
                'user_id' => (string) $userId,
                'document_type' => $documentType,
                'uploaded_at' => now()->toISOString(),
                'original_filename' => $file->getClientOriginalName(),
            ],
        ]);

        // Log document upload (personal data storage)
        $this->auditLogger->logPersonalDataCollection([
            'user_id' => $userId,
            'action' => 'document_uploaded',
            'document_type' => $documentType,
            'storage_location' => 's3://' . self::S3_DOCUMENTS_BUCKET . '/' . $s3Key,
            'legal_basis' => 'legal_obligation',
            'timestamp' => now(),
        ]);

        return response()->json([
            'message' => 'Document uploaded successfully',
            'document_type' => $documentType,
            'storage_reference' => $s3Key,
        ], 201);
    }

    /**
     * Send SMS verification code via Twilio
     */
    private function sendSmsVerification(string $phoneNumber, int $userId): void
    {
        try {
            // Send verification code via Twilio Verify
            $verification = $this->twilioClient->verify->v2
                ->services(self::TWILIO_VERIFY_SERVICE_SID)
                ->verifications
                ->create($phoneNumber, 'sms');

            $this->auditLogger->logPersonalDataAccess([
                'user_id' => $userId,
                'action' => 'sms_verification_sent',
                'data_shared_with' => 'twilio',
                'data_fields' => ['phone'],
                'legal_basis' => 'consent',
                'timestamp' => now(),
            ]);
        } catch (TwilioException $e) {
            // Log failure but don't block registration
            $this->auditLogger->logError([
                'action' => 'sms_verification_failed',
                'user_id' => $userId,
                'error' => $e->getMessage(),
            ]);
        }
    }

    /**
     * Send WhatsApp notification via Twilio WhatsApp Business API
     *
     * Uses approved message templates for transactional notifications.
     * Personal data (name, order details) may be included in template variables.
     */
    private function sendWhatsAppNotification(
        string $recipientPhone,
        string $templateName,
        array $templateVariables
    ): void {
        try {
            $this->twilioClient->messages->create(
                'whatsapp:' . $recipientPhone,
                [
                    'from' => self::WHATSAPP_FROM_NUMBER,
                    'body' => $this->renderWhatsAppTemplate($templateName, $templateVariables),
                ]
            );
        } catch (TwilioException $e) {
            $this->auditLogger->logError([
                'action' => 'whatsapp_notification_failed',
                'template' => $templateName,
                'error' => $e->getMessage(),
            ]);
        }
    }

    /**
     * Send welcome email via SendGrid
     * Shares personal data (name, email) with SendGrid for delivery
     */
    private function sendWelcomeEmailViaSendGrid(string $email, string $fullName): void
    {
        $sendgridMail = new SendGridMail();
        $sendgridMail->setFrom(new SendGridFrom('welcome@company.com', 'Customer Service'));
        $sendgridMail->addTo(new SendGridTo($email, $fullName));
        $sendgridMail->setSubject("Welcome to CustomerPortal, {$fullName}!");
        $sendgridMail->addDynamicTemplateData([
            'customer_name' => $fullName,
            'customer_email' => $email,
            'login_url' => config('app.url') . '/login',
        ]);
        $sendgridMail->setTemplateId(config('services.sendgrid.welcome_template_id'));

        $sendgrid = new \SendGrid(config('services.sendgrid.api_key'));
        $sendgrid->send($sendgridMail);
    }

    /**
     * Send data export download link via SendGrid
     */
    private function sendDataExportEmail(string $email, string $firstName, string $downloadUrl): void
    {
        $sendgridMail = new SendGridMail();
        $sendgridMail->setFrom(new SendGridFrom('privacy@company.com', 'Privacy Team'));
        $sendgridMail->addTo(new SendGridTo($email));
        $sendgridMail->setSubject('Your Personal Data Export is Ready');
        $sendgridMail->addDynamicTemplateData([
            'first_name' => $firstName,
            'download_url' => $downloadUrl,
            'expires_in' => '24 hours',
        ]);
        $sendgridMail->setTemplateId(config('services.sendgrid.data_export_template_id'));

        $sendgrid = new \SendGrid(config('services.sendgrid.api_key'));
        $sendgrid->send($sendgridMail);
    }

    /**
     * Send account deletion confirmation via SendGrid
     */
    private function sendAccountDeletionEmail(string $email): void
    {
        $sendgridMail = new SendGridMail();
        $sendgridMail->setFrom(new SendGridFrom('privacy@company.com', 'Privacy Team'));
        $sendgridMail->addTo(new SendGridTo($email));
        $sendgridMail->setSubject('Account Deletion Confirmation');
        $sendgridMail->setTemplateId(config('services.sendgrid.deletion_template_id'));

        $sendgrid = new \SendGrid(config('services.sendgrid.api_key'));
        $sendgrid->send($sendgridMail);
    }

    /**
     * Render a WhatsApp message template with variables
     */
    private function renderWhatsAppTemplate(string $templateName, array $variables): string
    {
        $templates = [
            'account_deletion_confirmation' => 'Your account has been deleted as requested. '
                . 'If you did not request this, please contact support immediately.',
            'order_confirmation' => 'Hi {{user_name}}, your order #{{order_id}} has been confirmed.',
            'verification_code' => 'Your verification code is: {{code}}. Valid for 10 minutes.',
        ];

        $template = $templates[$templateName] ?? '';
        foreach ($variables as $key => $value) {
            $template = str_replace('{{' . $key . '}}', $value, $template);
        }

        return $template;
    }

    /**
     * Search users by email (admin function - handles personal data)
     */
    public function searchUsersByEmail(Request $request): JsonResponse
    {
        $email = $request->input('email');

        if (!$email || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
            return response()->json(['error' => 'Valid email required'], 400);
        }

        $users = User::where('email', 'LIKE', '%' . $email . '%')
            ->select('id', 'first_name', 'last_name', 'email', 'created_at')
            ->get();

        // Log admin search of personal data
        $this->auditLogger->logPersonalDataSearch([
            'searched_by' => auth()->id(),
            'search_criteria' => ['email' => $email],
            'results_count' => $users->count(),
            'timestamp' => now(),
            'admin_function' => true
        ]);

        return response()->json([
            'search_term' => $email,
            'results' => $users->map(function($user) {
                return [
                    'id' => $user->id,
                    'name' => $user->first_name . ' ' . $user->last_name,
                    'email' => $user->email,
                    'created_at' => $user->created_at->toISOString()
                ];
            })
        ]);
    }

    /**
     * Handle Stripe webhook events
     *
     * Receives payment and customer events from Stripe.
     * May contain personal data in event payloads (customer email, name).
     */
    public function handleStripeWebhook(Request $request): JsonResponse
    {
        $payload = $request->getContent();
        $sigHeader = $request->header('Stripe-Signature');

        try {
            $event = \Stripe\Webhook::constructEvent(
                $payload,
                $sigHeader,
                self::STRIPE_WEBHOOK_SECRET
            );
        } catch (\Exception $e) {
            return response()->json(['error' => 'Webhook signature verification failed'], 400);
        }

        match ($event->type) {
            'payment_intent.succeeded' => $this->handlePaymentSuccess($event->data->object),
            'customer.deleted' => $this->handleStripeCustomerDeletion($event->data->object),
            'charge.refunded' => $this->handleRefund($event->data->object),
            default => null,
        };

        return response()->json(['received' => true]);
    }

    private function handlePaymentSuccess(object $paymentIntent): void
    {
        $userId = $paymentIntent->metadata->user_id ?? null;
        if ($userId) {
            $this->auditLogger->logPersonalDataAccess([
                'user_id' => $userId,
                'action' => 'payment_confirmed',
                'data_received_from' => 'stripe',
                'timestamp' => now(),
            ]);
        }
    }

    private function handleStripeCustomerDeletion(object $customer): void
    {
        // Stripe customer was deleted externally - log for audit trail
        $this->auditLogger->logPersonalDataDeletion([
            'action' => 'stripe_customer_deleted',
            'stripe_customer_id' => $customer->id,
            'timestamp' => now(),
        ]);
    }

    private function handleRefund(object $charge): void
    {
        // Refund processed - may need to update user records
        $this->auditLogger->logPersonalDataAccess([
            'action' => 'refund_processed',
            'stripe_charge_id' => $charge->id,
            'amount_refunded' => $charge->amount_refunded,
            'timestamp' => now(),
        ]);
    }
}

/**
 * Helper functions for personal data handling
 */
trait PersonalDataHelpers
{
    /**
     * Validate email format (commonly used for personal data)
     */
    private function validateEmailFormat(string $email): bool
    {
        return filter_var($email, FILTER_VALIDATE_EMAIL) !== false;
    }

    /**
     * Validate UK phone number format
     */
    private function validateUKPhone(string $phone): bool
    {
        // Matches: +44 20 7946 0958, 020 7946 0958, 07700 900123
        $pattern = '/^(\+44\s?|0)([1-9]\d{8,9})$/';
        return preg_match($pattern, preg_replace('/\s+/', '', $phone));
    }

    /**
     * Format name for display (handles personal data)
     */
    private function formatDisplayName(string $firstName, string $lastName): string
    {
        return trim($firstName . ' ' . $lastName);
    }
}
