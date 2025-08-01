<?php

class SmsService
{
    private $twilio_client;

    public function sendVerificationSms($phone_number, $verification_code)
    {
        $message = "Your verification code is: " . $verification_code;
        return $this->sendSms($phone_number, $message);
    }

    public function sendWelcomeSms($phone_number, $first_name)
    {
        $message = "Welcome " . $first_name . "! Thanks for joining us.";
        return $this->sendSms($phone_number, $message);
    }

    public function sendNotification($phone_number, $notification_text)
    {
        return $this->sendSms($phone_number, $notification_text);
    }

    public function validatePhoneNumber($phone_number)
    {
        return preg_match('/^\+?[1-9]\d{1,14}$/', $phone_number);
    }

    private function sendSms($phone_number, $message)
    {
        // Twilio SMS sending logic
        return true;
    }
}
