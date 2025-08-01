<?php

class PrivacyController
{
    public function handleDataRequest($user_email, $request_type)
    {
        switch ($request_type) {
            case 'export':
                return $this->exportUserData($user_email);
            case 'delete':
                return $this->deleteUserData($user_email);
            case 'rectify':
                return $this->rectifyUserData($user_email);
            default:
                return false;
        }
    }

    public function exportUserData($email_address)
    {
        $user_data = $this->getUserData($email_address);
        $activity_logs = $this->getUserActivityLogs($email_address);
        $payment_history = $this->getUserPaymentHistory($email_address);

        $export_data = [
            'personal_data' => $user_data,
            'activity_history' => $activity_logs,
            'payment_history' => $payment_history,
            'export_date' => date('Y-m-d H:i:s')
        ];

        $this->logPrivacyRequest($email_address, 'export');
        return json_encode($export_data, JSON_PRETTY_PRINT);
    }

    public function deleteUserData($user_email)
    {
        // GDPR Article 17 - Right to erasure
        $user_id = $this->getUserIdByEmail($user_email);

        if ($user_id) {
            $this->deleteFromTable('user_activity', 'user_id', $user_id);
            $this->deleteFromTable('payments', 'customer_id', $user_id);
            $this->deleteFromTable('addresses', 'user_id', $user_id);
            $this->deleteFromTable('users', 'id', $user_id);

            $this->logPrivacyRequest($user_email, 'delete');
            return true;
        }

        return false;
    }

    public function rectifyUserData($user_email, $corrections)
    {
        $user_id = $this->getUserIdByEmail($user_email);

        foreach ($corrections as $field => $new_value) {
            $this->updateUserField($user_id, $field, $new_value);
        }

        $this->logPrivacyRequest($user_email, 'rectify');
        return true;
    }

    private function getUserData($email)
    {
        $sql = "SELECT * FROM users WHERE email = ?";
        return $this->executeQuery($sql, [$email]);
    }

    private function getUserActivityLogs($email)
    {
        $sql = "SELECT * FROM user_activity WHERE user_id = (SELECT id FROM users WHERE email = ?)";
        return $this->executeQuery($sql, [$email]);
    }

    private function getUserPaymentHistory($email)
    {
        $sql = "SELECT * FROM payments WHERE customer_id = (SELECT id FROM users WHERE email = ?)";
        return $this->executeQuery($sql, [$email]);
    }

    private function getUserIdByEmail($email)
    {
        $sql = "SELECT id FROM users WHERE email = ?";
        $result = $this->executeQuery($sql, [$email]);
        return $result ? $result[0]['id'] : null;
    }

    private function deleteFromTable($table, $field, $value)
    {
        $sql = "DELETE FROM $table WHERE $field = ?";
        return $this->executeQuery($sql, [$value]);
    }

    private function updateUserField($user_id, $field, $value)
    {
        $sql = "UPDATE users SET $field = ? WHERE id = ?";
        return $this->executeQuery($sql, [$value, $user_id]);
    }

    private function logPrivacyRequest($email, $request_type)
    {
        $sql = "INSERT INTO privacy_requests (email, request_type, processed_at) VALUES (?, ?, NOW())";
        $this->executeQuery($sql, [$email, $request_type]);
    }

    private function executeQuery($sql, $params)
    {
        // Database query execution logic
        return [];
    }
}
