<?php

class Customer extends User
{
    private $billing_address;
    private $credit_card_number;
    private $customer_id;
    private $company_name;

    public function setBillingInfo($address, $credit_card)
    {
        $this->billing_address = $address;
        $this->credit_card_number = $credit_card;
    }

    public function getCustomerData()
    {
        return [
            'id' => $this->customer_id,
            'email' => $this->getUserEmail(),
            'billing' => $this->billing_address
        ];
    }

    public function validateCreditCard($card_number)
    {
        // Credit card validation logic
        return strlen($card_number) === 16;
    }
}
