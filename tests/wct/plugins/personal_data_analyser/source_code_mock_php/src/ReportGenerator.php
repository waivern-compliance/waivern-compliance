<?php

class ReportGenerator
{
    public function generateUserReport($user_id)
    {
        $sql = "SELECT u.email, u.first_name, u.last_name, u.phone, u.address,
                       COUNT(p.id) as payment_count, SUM(p.amount) as total_spent
                FROM users u
                LEFT JOIN payments p ON u.id = p.customer_id
                WHERE u.id = ?
                GROUP BY u.id";

        return $this->executeQuery($sql, [$user_id]);
    }

    public function generatePrivacyReport($user_id)
    {
        $user_data = $this->getUserPersonalData($user_id);
        $activity_data = $this->getUserActivityData($user_id);

        return [
            'personal_data' => $user_data,
            'activity_history' => $activity_data,
            'report_generated' => date('Y-m-d H:i:s')
        ];
    }

    public function exportUserDataForGDPR($user_id, $email_address)
    {
        $data = [
            'user_info' => $this->getUserPersonalData($user_id),
            'payment_history' => $this->getUserPaymentHistory($user_id),
            'activity_log' => $this->getUserActivityData($user_id),
            'file_uploads' => $this->getUserFileHistory($user_id)
        ];

        $this->logDataExport($user_id, $email_address);
        return json_encode($data, JSON_PRETTY_PRINT);
    }

    private function getUserPersonalData($user_id)
    {
        $sql = "SELECT email, first_name, last_name, phone, address, date_of_birth FROM users WHERE id = ?";
        return $this->executeQuery($sql, [$user_id]);
    }

    private function getUserActivityData($user_id)
    {
        $sql = "SELECT activity, ip_address, user_agent, timestamp FROM user_activity WHERE user_id = ?";
        return $this->executeQuery($sql, [$user_id]);
    }

    private function getUserPaymentHistory($user_id)
    {
        $sql = "SELECT amount, credit_card_last4, created_at FROM payments WHERE customer_id = ?";
        return $this->executeQuery($sql, [$user_id]);
    }

    private function getUserFileHistory($user_id)
    {
        $sql = "SELECT filename, upload_date FROM file_uploads WHERE user_id = ?";
        return $this->executeQuery($sql, [$user_id]);
    }

    private function logDataExport($user_id, $email)
    {
        $sql = "INSERT INTO data_exports (user_id, email, export_date) VALUES (?, ?, NOW())";
        $this->executeQuery($sql, [$user_id, $email]);
    }

    private function executeQuery($sql, $params)
    {
        // Database query execution logic
        return [];
    }
}
