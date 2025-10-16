<?php

class AuthController
{
    public function registerUser($email, $password, $first_name, $last_name)
    {
        // Hash password for security
        $hashed_password = password_hash($password, PASSWORD_DEFAULT);

        // Store user data in database
        $sql = "INSERT INTO users (email, password, first_name, last_name) VALUES (?, ?, ?, ?)";
        return $this->executeQuery($sql, [$email, $hashed_password, $first_name, $last_name]);
    }

    public function authenticateUser($email, $password)
    {
        $sql = "SELECT password FROM users WHERE email = ?";
        $result = $this->executeQuery($sql, [$email]);

        if ($result && password_verify($password, $result['password'])) {
            return $this->createUserSession($email);
        }
        return false;
    }

    public function resetPassword($email, $new_password)
    {
        $hashed_password = password_hash($new_password, PASSWORD_DEFAULT);
        $sql = "UPDATE users SET password = ? WHERE email = ?";
        return $this->executeQuery($sql, [$hashed_password, $email]);
    }

    private function executeQuery($sql, $params)
    {
        // Database query execution logic
        return true;
    }

    private function createUserSession($email)
    {
        $_SESSION['user_email'] = $email;
        return true;
    }
}
