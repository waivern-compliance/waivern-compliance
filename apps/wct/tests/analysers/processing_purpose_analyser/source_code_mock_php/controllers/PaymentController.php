<?php

class PaymentController
{
    public function processPayment($customer_id, $credit_card_number, $amount)
    {
        // Validate credit card
        if (!$this->validateCreditCard($credit_card_number)) {
            return false;
        }

        // Process payment with Stripe
        $stripe_result = $this->chargeStripe($credit_card_number, $amount);

        // Store transaction
        $sql = "INSERT INTO payments (customer_id, amount, credit_card_last4) VALUES (?, ?, ?)";
        $last4 = substr($credit_card_number, -4);
        $this->executeQuery($sql, [$customer_id, $amount, $last4]);

        return $stripe_result;
    }

    public function getPaymentHistory($customer_id)
    {
        $sql = "SELECT * FROM payments WHERE customer_id = ?";
        return $this->executeQuery($sql, [$customer_id]);
    }

    private function validateCreditCard($card_number)
    {
        // Credit card validation logic
        return preg_match('/^\d{16}$/', $card_number);
    }

    private function chargeStripe($card_number, $amount)
    {
        // Stripe API integration
        return true;
    }

    private function executeQuery($sql, $params)
    {
        // Database query execution logic
        return [];
    }
}
