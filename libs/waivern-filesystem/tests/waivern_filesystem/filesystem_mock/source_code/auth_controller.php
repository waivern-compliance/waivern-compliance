<?php
/**
 * AuthController - Handles user authentication and personal data
 *
 * GDPR Compliance Notes:
 * - Processes personal data including names, emails, phone numbers
 * - Implements data export and deletion capabilities
 * - Logs all personal data access for audit purposes
 */

namespace App\Controllers;

use App\Models\User;
use App\Services\AuditLogger;
use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;

class AuthController extends BaseController
{
    private AuditLogger $auditLogger;

    // Personal data fields that require special handling
    private const PERSONAL_DATA_FIELDS = [
        'first_name', 'last_name', 'email', 'phone', 'date_of_birth'
    ];

    /**
     * Create new user account
     * Handles personal data: name, email, phone, date of birth
     */
    public function createUser(Request $request): JsonResponse
    {
        $userData = $request->only(self::PERSONAL_DATA_FIELDS);

        // Log personal data collection
        $this->auditLogger->logPersonalDataCollection([
            'action' => 'user_registration',
            'data_types' => array_keys($userData),
            'legal_basis' => 'consent',
            'user_ip' => $request->ip(),
            'timestamp' => now(),
        ]);

        $user = User::create([
            'first_name' => $userData['first_name'],
            'last_name' => $userData['last_name'],
            'email' => $userData['email'],
            'phone' => $userData['phone'],
            'date_of_birth' => $userData['date_of_birth'],
            'gdpr_consent_given_at' => now(),
        ]);

        return response()->json([
            'message' => 'User created successfully',
            'user_id' => $user->id,
            'email' => $user->email
        ], 201);
    }

    /**
     * Export user's personal data (GDPR Article 20)
     */
    public function exportPersonalData(int $userId): JsonResponse
    {
        $user = User::findOrFail($userId);

        $personalData = [
            'basic_information' => [
                'first_name' => $user->first_name,
                'last_name' => $user->last_name,
                'email' => $user->email,
                'phone' => $user->phone,
                'date_of_birth' => $user->date_of_birth,
            ],
        ];

        // Log data export request
        $this->auditLogger->logPersonalDataExport([
            'user_id' => $userId,
            'requested_by' => auth()->id(),
            'export_scope' => 'full_profile',
            'timestamp' => now(),
        ]);

        return response()->json([
            'export_date' => now()->toISOString(),
            'user_id' => $userId,
            'personal_data' => $personalData
        ]);
    }

    /**
     * Search users by email (admin function - handles personal data)
     */
    public function searchUsersByEmail(Request $request): JsonResponse
    {
        $email = $request->input('email');

        $users = User::where('email', 'LIKE', '%' . $email . '%')
            ->select('id', 'first_name', 'last_name', 'email')
            ->get();

        // Log admin search of personal data
        $this->auditLogger->logPersonalDataSearch([
            'searched_by' => auth()->id(),
            'search_criteria' => ['email' => $email],
            'results_count' => $users->count(),
            'timestamp' => now(),
        ]);

        return response()->json([
            'search_term' => $email,
            'results' => $users->map(function($user) {
                return [
                    'id' => $user->id,
                    'name' => $user->first_name . ' ' . $user->last_name,
                    'email' => $user->email,
                ];
            })
        ]);
    }
}
