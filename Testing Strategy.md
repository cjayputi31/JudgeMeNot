# **Testing Strategy & Compliance Report**

## **1\. Automated Test Coverage**

We have implemented unit and integration tests using the unittest framework.  
To run the automated test suite:  
python \-m unittest tests/test\_core\_logic.py

### **Test Suite Breakdown**

| Category | Test Case | Description |
| :---- | :---- | :---- |
| **Unit** | test\_user\_creation | Verifies Admin can create users and passwords are hashed. |
| **Unit** | test\_auth\_flow | Verifies Login Success (valid creds) and Failure (invalid creds). |
| **Unit** | test\_role\_enforcement | Verifies Judges can only access events they are assigned to. |
| **Enhancement** | test\_security\_audit\_logging | **Security Feature:** Ensures LOGIN events are written to the database. |
| **Enhancement** | test\_multi\_platform\_logic | **Multi-Platform:** Validates the User Agent parsing logic for Android detection. |
| **Integration** | test\_integration\_event\_lifecycle | Simulates full workflow: Create Event \-\> Add Round \-\> Activate Round. |

## **2\. Manual Test Matrix (Exploratory Testing)**

This matrix covers UI interactions and edge cases that are difficult to unit test.

| ID | Test Scenario | Steps | Expected Result | Status |
| :---- | :---- | :---- | :---- | :---- |
| **MAN-01** | **Login Guard** | 1\. Open App. 2\. Enter invalid password. | Error message "Invalid credentials" appears. | ✅ Pass |
| **MAN-02** | **Role Access** | 1\. Login as Judge. 2\. Manually change URL to /admin. | System redirects user back to Login immediately. | ✅ Pass |
| **MAN-03** | **Password Change** | 1\. Admin selects a user. 2\. Updates password. 3\. User logs in with new password. | Login successful with new credentials. | ✅ Pass |
| **MAN-04** | **Restricted Action** | 1\. Login as AdminViewer (Auditor). 2\. Navigate to Event Config. | "Add" and "Delete" buttons are hidden or disabled. | ✅ Pass |
| **MAN-05** | **Android Lock** | 1\. Open Chrome DevTools. 2\. Set Device to "Pixel 5". 3\. Access /login. | App auto-redirects to /leaderboard. Login is inaccessible. | ✅ Pass |
| **MAN-06** | **Offline/Sync** | 1\. Disconnect DB. 2\. Attempt Login. | App shows "Connection Error" Snackbar instead of crashing. | ✅ Pass |
| **MAN-07** | **Calculations** | 1\. Enter scores: 90 (40%), 80 (60%). 2\. Check Result. | Total is exactly **84.0**. | ✅ Pass |

## **3\. Static Analysis & Code Quality**

We adhere to PEP 8 standards using ruff (or flake8) for linting and black for formatting.

### **Run Static Analysis**

To check for code quality issues:

pip install ruff  
ruff check .

### **Run Formatter**

To automatically format code to standards:

pip install black  
black .

### **Configuration**

* **Line Length:** 120 characters (optimized for modern screens).  
* **Quotes:** Double quotes preference.  
* **Imports:** Sorted automatically.