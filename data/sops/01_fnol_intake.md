# SOP-INT FNOL intake (SYNTHETIC)

> Synthetic claims-handling procedure written for the ClaimFlow demonstration (fictional insurer Northwind Mutual).

### SOP-INT-1.1 Logging the notice
Every first notice of loss (FNOL) is logged with the time it was received. The time the email arrived counts as the time of notice.

### SOP-INT-1.2 Facts to capture
Capture the claimant's name, policy number, line of business, incident date, incident type, a short description, the location and the documents attached.

### SOP-INT-1.3 Severity
Severity is high if the claim involves bodily injury, theft of a vehicle, fire, an emergency hospital admission, or an estimated loss of Rs 5,00,000 or more. Otherwise severity is medium if the estimated loss is between Rs 50,000 and Rs 4,99,999, or the claim involves a planned hospital admission. Otherwise severity is low. If none of these facts is known, severity is low.

### SOP-INT-1.4 Unclear line of business
If the line of business cannot be determined from the notice, refer the claim to a senior handler before any other step.
