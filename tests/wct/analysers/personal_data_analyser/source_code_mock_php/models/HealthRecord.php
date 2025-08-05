<?php

class HealthRecord
{
    private $patient_id;
    private $medical_history;
    private $diagnosis;
    private $treatment_plan;
    private $doctor_notes;
    private $insurance_info;

    public function createHealthRecord($patient_id, $diagnosis)
    {
        $this->patient_id = $patient_id;
        $this->diagnosis = $diagnosis;
    }

    public function addMedicalHistory($history)
    {
        $this->medical_history = $history;
    }

    public function updateTreatmentPlan($plan)
    {
        $this->treatment_plan = $plan;
    }

    public function getPatientData()
    {
        return [
            'patient_id' => $this->patient_id,
            'diagnosis' => $this->diagnosis,
            'treatment' => $this->treatment_plan
        ];
    }
}
