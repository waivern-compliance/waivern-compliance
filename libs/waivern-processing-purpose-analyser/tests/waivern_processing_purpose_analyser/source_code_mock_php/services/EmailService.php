<?php

class EmailService
{
    private $mailer_config;

    public function sendWelcomeEmail($user_email, $first_name)
    {
        $subject = "Welcome " . $first_name;
        $body = "Welcome to our service, " . $first_name . "!";

        return $this->sendEmail($user_email, $subject, $body);
    }

    public function sendPasswordResetEmail($email_address, $reset_token)
    {
        $subject = "Password Reset Request";
        $body = "Click here to reset your password: " . $reset_token;

        return $this->sendEmail($email_address, $subject, $body);
    }

    public function sendNewsLetter($email_list)
    {
        foreach ($email_list as $email) {
            $this->sendEmail($email, "Newsletter", "Our latest news...");
        }
    }

    public function validateEmail($email_address)
    {
        return filter_var($email_address, FILTER_VALIDATE_EMAIL);
    }

    private function sendEmail($to_email, $subject, $body)
    {
        // Email sending logic using SendGrid
        return mail($to_email, $subject, $body);
    }
}
