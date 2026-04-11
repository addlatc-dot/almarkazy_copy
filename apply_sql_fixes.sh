#!/bin/bash

# Read the corrected SQL file
cp hospi_corrected.sql hospi_final_fixed.sql

# Fix 1: Remove circular FK on berth_date
sed -i '/ADD CONSTRAINT `berth_date` FOREIGN KEY (`berth_date`) REFERENCES `patient` (`berth_date`),/d' hospi_final_fixed.sql

# Fix 2: Add FK for doctor.current_patient -> patient.id (before the last ADD CONSTRAINT in doctor table)
# Find the doctor table ALTER section and add the FK before the last one

# First, let's add the FK for doctor.current_patient
# We'll find the line with "ADD CONSTRAINT `section_id`" in doctor table and add after it

sed -i '/ALTER TABLE `doctor`/,/;/{
  s/ADD CONSTRAINT `section_id`/ADD CONSTRAINT `doctor_patient_fk` FOREIGN KEY (`current_patient`) REFERENCES `patient` (`id`) ON DELETE SET NULL,\n  ADD CONSTRAINT `section_id`/
}' hospi_final_fixed.sql

# Fix 3: Add FK for section.doctor_id -> doctor.id (in section table)
# Find the section table and add the FK

sed -i '/ALTER TABLE `section`/,/;/{
  s/;$/,\n  ADD CONSTRAINT `section_doctor_fk` FOREIGN KEY (`doctor_id`) REFERENCES `doctor` (`id`) ON DELETE SET NULL;/
}' hospi_final_fixed.sql

echo "✓ SQL fixes applied successfully!"
echo "✓ Circular FK removed (berth_date)"
echo "✓ FK added: doctor.current_patient -> patient.id"
echo "✓ FK added: section.doctor_id -> doctor.id"
