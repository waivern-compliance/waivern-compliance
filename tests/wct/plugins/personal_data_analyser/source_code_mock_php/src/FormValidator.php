<?php

class FormValidator
{
    public function validateUserRegistration($email, $password, $first_name, $last_name, $phone)
    {
        $errors = [];

        if (!$this->validateEmail($email)) {
            $errors[] = "Invalid email address";
        }

        if (!$this->validatePassword($password)) {
            $errors[] = "Password must be at least 8 characters";
        }

        if (!$this->validateName($first_name)) {
            $errors[] = "Invalid first name";
        }

        if (!$this->validateName($last_name)) {
            $errors[] = "Invalid last name";
        }

        if (!$this->validatePhone($phone)) {
            $errors[] = "Invalid phone number";
        }

        return $errors;
    }

    public function validateCreditCardInfo($credit_card_number, $billing_address)
    {
        $errors = [];

        if (!$this->validateCreditCard($credit_card_number)) {
            $errors[] = "Invalid credit card number";
        }

        if (empty($billing_address)) {
            $errors[] = "Billing address is required";
        }

        return $errors;
    }

    private function validateEmail($email_address)
    {
        return filter_var($email_address, FILTER_VALIDATE_EMAIL);
    }

    private function validatePassword($password)
    {
        return strlen($password) >= 8;
    }

    private function validateName($name)
    {
        return !empty($name) && strlen($name) <= 50;
    }

    private function validatePhone($phone_number)
    {
        return preg_match('/^\+?[1-9]\d{1,14}$/', $phone_number);
    }

    private function validateCreditCard($credit_card_number)
    {
        return preg_match('/^\d{16}$/', $credit_card_number);
    }
}
