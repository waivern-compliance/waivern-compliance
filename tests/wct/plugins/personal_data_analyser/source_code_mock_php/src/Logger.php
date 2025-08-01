<?php

class Logger
{
    private $log_file;

    public function __construct($log_file = '/var/log/app.log')
    {
        $this->log_file = $log_file;
    }

    public function logUserAction($user_id, $user_email, $action, $context = [])
    {
        $log_entry = [
            'timestamp' => date('Y-m-d H:i:s'),
            'user_id' => $user_id,
            'email' => $user_email,
            'action' => $action,
            'ip_address' => $_SERVER['REMOTE_ADDR'] ?? 'unknown',
            'user_agent' => $_SERVER['HTTP_USER_AGENT'] ?? 'unknown',
            'context' => $context
        ];

        $this->writeToLog($log_entry);
        $this->saveToDatabase($log_entry);
    }

    public function logPersonalDataAccess($user_id, $accessed_email, $data_type, $access_purpose)
    {
        $log_entry = [
            'timestamp' => date('Y-m-d H:i:s'),
            'event_type' => 'personal_data_access',
            'user_id' => $user_id,
            'accessed_email' => $accessed_email,
            'data_type' => $data_type,
            'purpose' => $access_purpose,
            'ip_address' => $_SERVER['REMOTE_ADDR'] ?? 'unknown'
        ];

        $this->writeToLog($log_entry);
        $this->saveToDatabase($log_entry);
    }

    public function logSecurityEvent($event_type, $user_email, $details)
    {
        $log_entry = [
            'timestamp' => date('Y-m-d H:i:s'),
            'event_type' => 'security_event',
            'security_event' => $event_type,
            'user_email' => $user_email,
            'details' => $details,
            'ip_address' => $_SERVER['REMOTE_ADDR'] ?? 'unknown'
        ];

        $this->writeToLog($log_entry);
        $this->saveToDatabase($log_entry);
    }

    public function getLogsByEmail($email_address, $start_date = null, $end_date = null)
    {
        $sql = "SELECT * FROM system_logs WHERE email = ? OR accessed_email = ?";
        $params = [$email_address, $email_address];

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

    private function writeToLog($log_entry)
    {
        $log_line = json_encode($log_entry) . "\n";
        file_put_contents($this->log_file, $log_line, FILE_APPEND | LOCK_EX);
    }

    private function saveToDatabase($log_entry)
    {
        $sql = "INSERT INTO system_logs (timestamp, user_id, email, action, ip_address, details) VALUES (?, ?, ?, ?, ?, ?)";
        $this->executeQuery($sql, [
            $log_entry['timestamp'],
            $log_entry['user_id'] ?? null,
            $log_entry['email'] ?? $log_entry['accessed_email'] ?? $log_entry['user_email'] ?? null,
            $log_entry['action'] ?? $log_entry['event_type'] ?? null,
            $log_entry['ip_address'],
            json_encode($log_entry)
        ]);
    }

    private function executeQuery($sql, $params)
    {
        // Database query execution logic
        return [];
    }
}
