<?php

class PasswordManager
{
    public function hashPassword($plain_password)
    {
        return password_hash($plain_password, PASSWORD_DEFAULT);
    }

    public function verifyPassword($plain_password, $hashed_password)
    {
        return password_verify($plain_password, $hashed_password);
    }

    public function generateResetToken($user_email)
    {
        $token = bin2hex(random_bytes(32));
        $expiry = date('Y-m-d H:i:s', strtotime('+1 hour'));

        $sql = "INSERT INTO password_resets (email, token, expires_at) VALUES (?, ?, ?)";
        $this->executeQuery($sql, [$user_email, $token, $expiry]);

        return $token;
    }

    public function validateResetToken($token, $email_address)
    {
        $sql = "SELECT email FROM password_resets WHERE token = ? AND email = ? AND expires_at > NOW()";
        $result = $this->executeQuery($sql, [$token, $email_address]);

        return !empty($result);
    }

    public function updatePassword($email, $new_password)
    {
        $hashed_password = $this->hashPassword($new_password);
        $sql = "UPDATE users SET password = ? WHERE email = ?";
        return $this->executeQuery($sql, [$hashed_password, $email]);
    }

    public function logPasswordChange($user_id, $user_email, $ip_address)
    {
        $sql = "INSERT INTO password_changes (user_id, email, ip_address, changed_at) VALUES (?, ?, ?, NOW())";
        $this->executeQuery($sql, [$user_id, $user_email, $ip_address]);
    }

    private function executeQuery($sql, $params)
    {
        // Database query execution logic
        return [];
    }
}
