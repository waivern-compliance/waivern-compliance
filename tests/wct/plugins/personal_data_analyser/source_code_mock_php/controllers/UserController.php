<?php

class UserController
{
    public function getUserProfile($user_id)
    {
        $sql = "SELECT first_name, last_name, email, phone FROM users WHERE id = ?";
        return $this->executeQuery($sql, [$user_id]);
    }

    public function updateUserProfile($user_id, $first_name, $last_name, $phone)
    {
        $sql = "UPDATE users SET first_name = ?, last_name = ?, phone = ? WHERE id = ?";
        return $this->executeQuery($sql, [$first_name, $last_name, $phone, $user_id]);
    }

    public function deleteUser($user_id)
    {
        // GDPR compliant user deletion
        $sql = "DELETE FROM users WHERE id = ?";
        return $this->executeQuery($sql, [$user_id]);
    }

    public function getUserByEmail($email_address)
    {
        $sql = "SELECT * FROM users WHERE email = ?";
        return $this->executeQuery($sql, [$email_address]);
    }

    public function exportUserData($user_id)
    {
        // GDPR data portability
        $sql = "SELECT * FROM users WHERE id = ?";
        $userData = $this->executeQuery($sql, [$user_id]);

        return json_encode($userData);
    }

    private function executeQuery($sql, $params)
    {
        // Database query execution logic
        return [];
    }
}
