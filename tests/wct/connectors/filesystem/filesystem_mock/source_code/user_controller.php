<?php
/**
 * UserController - Handles user account operations
 *
 * GDPR Compliance Notes:
 * - Processes personal data including names, emails, phone numbers
 * - Implements data minimization principles
 * - Provides data export and deletion capabilities
 * - Logs all personal data access for audit purposes
 */

namespace App\Controllers;

use App\Models\User;
use App\Models\Address;
use App\Services\EmailService;
use App\Services\AuditLogger;
use App\Services\EncryptionService;
use App\Exceptions\ValidationException;
use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Validator;

class UserController extends BaseController implements GDPRCompliantController
{
    private EmailService $emailService;
    private AuditLogger $auditLogger;
    private EncryptionService $encryption;

    // Personal data fields that require special handling
    private const PERSONAL_DATA_FIELDS = [
        'first_name', 'last_name', 'email', 'phone',
        'date_of_birth', 'national_id', 'address'
    ];

    public function __construct(
        EmailService $emailService,
        AuditLogger $auditLogger,
        EncryptionService $encryption
    ) {
        $this->emailService = $emailService;
        $this->auditLogger = $auditLogger;
        $this->encryption = $encryption;
    }

    /**
     * Create new user account
     * Handles personal data: name, email, phone, date of birth
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

        // Send welcome email with personal data
        $this->emailService->sendWelcomeEmail(
            $user->email,
            $user->first_name . ' ' . $user->last_name
        );

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

        // Log personal data modification
        $this->auditLogger->logPersonalDataModification([
            'user_id' => $userId,
            'modified_by' => auth()->id(),
            'original_data' => $originalData,
            'new_data' => $request->only(self::PERSONAL_DATA_FIELDS),
            'modified_fields' => array_keys($updateData),
            'timestamp' => now()
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

        // Log data export request
        $this->auditLogger->logPersonalDataExport([
            'user_id' => $userId,
            'requested_by' => auth()->id(),
            'export_scope' => 'full_profile',
            'data_categories' => ['basic_info', 'addresses', 'orders', 'support'],
            'timestamp' => now(),
            'legal_basis' => 'data_portability_request'
        ]);

        return response()->json([
            'export_date' => now()->toISOString(),
            'user_id' => $userId,
            'personal_data' => $personalData
        ]);
    }

    /**
     * Delete user account and personal data (GDPR Article 17)
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

        // Anonymize instead of hard delete for business records
        $user->update([
            'first_name' => 'DELETED',
            'last_name' => 'USER',
            'email' => 'deleted_user_' . $userId . '@anonymized.local',
            'phone' => null,
            'date_of_birth' => null,
            'deleted_at' => now()
        ]);

        // Remove addresses (contain personal data)
        $user->addresses()->delete();

        // Send deletion confirmation (if email still exists)
        if ($user->email && !str_contains($user->email, 'anonymized.local')) {
            $this->emailService->sendAccountDeletionConfirmation($user->email);
        }

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

        return response()->json(['message' => 'Consent withdrawn successfully']);
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
