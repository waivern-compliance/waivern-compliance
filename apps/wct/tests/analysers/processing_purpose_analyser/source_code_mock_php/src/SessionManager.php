<?php

class SessionManager
{
    public function startUserSession($user_id, $email_address, $first_name)
    {
        session_start();
        $_SESSION['user_id'] = $user_id;
        $_SESSION['email'] = $email_address;
        $_SESSION['first_name'] = $first_name;
        $_SESSION['login_time'] = time();
    }

    public function getUserFromSession()
    {
        if (isset($_SESSION['user_id'])) {
            return [
                'id' => $_SESSION['user_id'],
                'email' => $_SESSION['email'],
                'first_name' => $_SESSION['first_name']
            ];
        }
        return null;
    }

    public function updateSessionData($key, $value)
    {
        $_SESSION[$key] = $value;
    }

    public function destroyUserSession()
    {
        session_start();
        unset($_SESSION['user_id']);
        unset($_SESSION['email']);
        unset($_SESSION['first_name']);
        session_destroy();
    }

    public function isUserLoggedIn()
    {
        return isset($_SESSION['user_id']) && isset($_SESSION['email']);
    }
}
