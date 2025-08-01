<?php

class CookieManager
{
    public function setUserPreferences($user_id, $email, $preferences)
    {
        setcookie('user_id', $user_id, time() + 3600, '/');
        setcookie('user_email', $email, time() + 3600, '/');
        setcookie('preferences', json_encode($preferences), time() + 3600, '/');
    }

    public function getUserFromCookie()
    {
        if (isset($_COOKIE['user_id']) && isset($_COOKIE['user_email'])) {
            return [
                'id' => $_COOKIE['user_id'],
                'email' => $_COOKIE['user_email']
            ];
        }
        return null;
    }

    public function setTrackingCookie($visitor_id, $user_agent, $ip_address)
    {
        $tracking_data = [
            'visitor_id' => $visitor_id,
            'user_agent' => $user_agent,
            'ip_address' => $ip_address,
            'timestamp' => time()
        ];

        setcookie('tracking', json_encode($tracking_data), time() + 86400, '/');
    }

    public function clearUserCookies()
    {
        setcookie('user_id', '', time() - 3600, '/');
        setcookie('user_email', '', time() - 3600, '/');
        setcookie('preferences', '', time() - 3600, '/');
        setcookie('tracking', '', time() - 3600, '/');
    }

    public function hasConsentCookie()
    {
        return isset($_COOKIE['gdpr_consent']);
    }

    public function setConsentCookie($consent_data)
    {
        setcookie('gdpr_consent', json_encode($consent_data), time() + 31536000, '/');
    }
}
