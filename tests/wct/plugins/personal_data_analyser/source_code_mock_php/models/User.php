<?php

class User
{
    private $user_id;
    private $email_address;
    private $first_name;
    private $last_name;
    private $date_of_birth;
    private $phone_number;
    private $social_security_number;

    public function __construct($email, $first_name, $last_name)
    {
        $this->email_address = $email;
        $this->first_name = $first_name;
        $this->last_name = $last_name;
    }

    public function getUserEmail()
    {
        return $this->email_address;
    }

    public function setPersonalData($phone, $ssn, $dob)
    {
        $this->phone_number = $phone;
        $this->social_security_number = $ssn;
        $this->date_of_birth = $dob;
    }
}
