# Amazon BDays 🎁

### 01 GET CSV

```
A
Go to Amazon 🎁 (https://contacts.google.com/label/593e0aec0fc2b1a4)
& Amazon B&G 🎁 (https://contacts.google.com/label/f2f084c8f60c8f8)

B
Export to "Google CSV"
```

### 02 CLEAN CSV

```
A
Delete in bulk each these columns until only these rename
"First Name,Last Name,Birthday,E-mail 1 - Value"

B
Rename columns to "First Name,Last Name,Birthday,Email"
Add B&G column with "X" to Amazon B&G 🎁 and add to contacts-amazon.csv
Might need to add a "," to the end of the file

C
Change all "Birthday"s to the previous year (i.e "2025")
split into 4 files by date - (Q1, Q2, etc.)
This will show the "git diff" to see what's changed - commit that
then change to current year (i.e. "2026") and commit again
```

### 03 RUN CHROME EXTENSION

```
A
Start with just 1-2 entries to debug date and redirect
i.e "Will,Clark,2024-01-28,clark.will19@gmail.com,Sam,Selig,2024-01-30,jsamselig@gmail.com,"

B
Navigate to chrome://extensions/
Click "Load Unpacked" from this folder

C
Make sure desktop not mobile
Make sure redirect URL is correct
Navigate to https://www.amazon.com/dp/B0FLDMPWBR?th=1&gpo=20
Start Automation

D
Be patient
Errors will happen
if so - Remove Extension
Update CSV to pending names
Re-run the script

E
Remove Extension
Check the emails
PURCHASE - move to next Q
```

# Archive 🗄️

## Dec 30 2025 7:00-9:11 WITA

```js
URL NEW
"https://www.amazon.com/dp/B0FLDMPWBR?th=1&gpo=20"
URL OLD
"https://www.amazon.com/gp/product/B0D1TK5XVL"

Price NEW/OLD
document.getElementById("gc-order-form-custom-amount").value = 20;

Email NEW
document.getElementById("gc-email-recipients").value = bdayData.Email;
Email OLD
document.getElementById("gc-order-form-recipients").value = bdayData.Email;

Message NEW
document.getElementById("gc-from-input-Email").value = "Brendan OBrien";
document.getElementById(
    "gc-message-input-Email"
).value = `Happy Bday ${bdayData["First Name"]} from Brendan O`;
Message OLD
document.getElementById("gc-order-form-senderName").value =
  "Brendan OBrien";
document.getElementById(
  "gc-order-form-message"
).value = `Happy Bday ${bdayData["First Name"]} from Brendan O`;

Date Picker NEW
document.querySelector('span[data-action="a-cal-icon"]').click();
Date Picker OLD
document.getElementById("gc-order-form-date-val").click();

Month Arrow NEW
document.getElementsByClassName("a-declarative a-cal-paginate-next")[0].click();
Month Arrow OLD
document.getElementsByClassName("a-icon a-icon-next")[1].click();

Date NEW/OLD
document
    .getElementsByClassName(`a-cal-d a-cal-d-${bdayTimestamp}`)[0]
    .children[0].click();

Submit NEW
document.getElementById("add-to-cart-button").click();
Submit OLD
document.getElementById("gc-buy-box-atc").click();

```

### 6:00 WITA

```
104 + 2 B&G = 106
```

## Jan 21 2025 15:35

### BUG

```
cacton@alumni.nd.edu - ERROR
pgfsligo@oh.rr.com - ERROR
"Email address must contain a domain, like chris@example.com"
```

instead I said this

```
Happy Bday Caroline from Brendan O
NOTE: Kevin forward this to Caroline for me.
For some reason, her email "cactonATalumniDOTndDOTedu"
wasn't being accepted by amazon's form validation.
```

## Jan 21 2025 15:00

## Jan 19 2025 12:26
