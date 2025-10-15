<?php

class ApiClient
{
    private $base_url;
    private $api_key;

    public function __construct($base_url, $api_key)
    {
        $this->base_url = $base_url;
        $this->api_key = $api_key;
    }

    public function syncUserDataToFacebook($user_id, $email, $first_name, $phone)
    {
        $data = [
            'user_id' => $user_id,
            'email' => $email,
            'first_name' => $first_name,
            'phone' => $phone
        ];

        return $this->makeApiCall('/facebook/sync', $data);
    }

    public function sendUserDataToMailgun($email_address, $first_name, $preferences)
    {
        $data = [
            'email' => $email_address,
            'name' => $first_name,
            'preferences' => $preferences
        ];

        return $this->makeApiCall('/mailgun/subscribe', $data);
    }

    public function trackUserWithGoogle($user_id, $email, $behavior_data)
    {
        $tracking_data = [
            'user_id' => $user_id,
            'email' => $email,
            'events' => $behavior_data,
            'timestamp' => time()
        ];

        return $this->makeApiCall('/google/analytics', $tracking_data);
    }

    public function processPaymentWithStripe($customer_email, $credit_card_token, $amount)
    {
        $payment_data = [
            'email' => $customer_email,
            'token' => $credit_card_token,
            'amount' => $amount
        ];

        return $this->makeApiCall('/stripe/charge', $payment_data);
    }

    private function makeApiCall($endpoint, $data)
    {
        $url = $this->base_url . $endpoint;
        $headers = [
            'Authorization: Bearer ' . $this->api_key,
            'Content-Type: application/json'
        ];

        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

        $response = curl_exec($ch);
        curl_close($ch);

        return json_decode($response, true);
    }
}
