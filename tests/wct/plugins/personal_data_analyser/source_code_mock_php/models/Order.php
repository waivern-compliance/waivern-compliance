<?php

class Order
{
    private $order_id;
    private $customer_id;
    private $customer_email;
    private $billing_address;
    private $shipping_address;
    private $total_amount;
    private $payment_method;

    public function createOrder($customer_id, $customer_email, $billing_address, $shipping_address)
    {
        $this->customer_id = $customer_id;
        $this->customer_email = $customer_email;
        $this->billing_address = $billing_address;
        $this->shipping_address = $shipping_address;
    }

    public function processPayment($credit_card_info, $amount)
    {
        $this->total_amount = $amount;
        // Process payment
        return $this->chargeCustomer($credit_card_info, $amount);
    }

    public function getOrderDetails()
    {
        return [
            'order_id' => $this->order_id,
            'customer_email' => $this->customer_email,
            'billing_address' => $this->billing_address,
            'shipping_address' => $this->shipping_address,
            'total_amount' => $this->total_amount
        ];
    }

    public function updateShippingAddress($new_address)
    {
        $this->shipping_address = $new_address;
    }

    private function chargeCustomer($credit_card_info, $amount)
    {
        // Payment processing logic
        return true;
    }
}
