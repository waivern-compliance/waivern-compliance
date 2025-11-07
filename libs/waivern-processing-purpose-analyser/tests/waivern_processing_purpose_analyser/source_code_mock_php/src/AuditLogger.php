<?php

class AuditLogger
{
    public function logUserLogin($user_id, $email, $ip_address, $user_agent)
    {
        $log_data = [
            'event' => 'user_login',
            'user_id' => $user_id,
            'email' => $email,
            'ip_address' => $ip_address,
            'user_agent' => $user_agent,
            'timestamp' => date('Y-m-d H:i:s')
        ];

        $this->writeAuditLog($log_data);
    }

    public function logDataAccess($user_id, $accessed_data_type, $accessed_user_email)
    {
        $log_data = [
            'event' => 'data_access',
            'user_id' => $user_id,
            'data_type' => $accessed_data_type,
            'accessed_email' => $accessed_user_email,
            'timestamp' => date('Y-m-d H:i:s')
        ];

        $this->writeAuditLog($log_data);
    }

    public function logDataExport($user_id, $email, $export_type, $exported_records_count)
    {
        $log_data = [
            'event' => 'data_export',
            'user_id' => $user_id,
            'email' => $email,
            'export_type' => $export_type,
            'records_count' => $exported_records_count,
            'timestamp' => date('Y-m-d H:i:s')
        ];

        $this->writeAuditLog($log_data);
    }

    public function logPersonalDataModification($user_id, $modified_email, $field_changed, $old_value, $new_value)
    {
        $log_data = [
            'event' => 'personal_data_modification',
            'user_id' => $user_id,
            'modified_email' => $modified_email,
            'field' => $field_changed,
            'old_value' => $old_value,
            'new_value' => $new_value,
            'timestamp' => date('Y-m-d H:i:s')
        ];

        $this->writeAuditLog($log_data);
    }

    public function getAuditLogs($user_email = null, $start_date = null, $end_date = null)
    {
        $sql = "SELECT * FROM audit_logs WHERE 1=1";
        $params = [];

        if ($user_email) {
            $sql .= " AND (email = ? OR accessed_email = ? OR modified_email = ?)";
            $params[] = $user_email;
            $params[] = $user_email;
            $params[] = $user_email;
        }

        if ($start_date) {
            $sql .= " AND timestamp >= ?";
            $params[] = $start_date;
        }

        if ($end_date) {
            $sql .= " AND timestamp <= ?";
            $params[] = $end_date;
        }

        return $this->executeQuery($sql, $params);
    }

    private function writeAuditLog($log_data)
    {
        $sql = "INSERT INTO audit_logs (event, user_id, email, data_type, timestamp, details) VALUES (?, ?, ?, ?, ?, ?)";
        $details = json_encode($log_data);
        $this->executeQuery($sql, [
            $log_data['event'],
            $log_data['user_id'] ?? null,
            $log_data['email'] ?? $log_data['accessed_email'] ?? $log_data['modified_email'] ?? null,
            $log_data['data_type'] ?? null,
            $log_data['timestamp'],
            $details
        ]);
    }

    private function executeQuery($sql, $params)
    {
        // Database query execution logic
        return [];
    }
}
