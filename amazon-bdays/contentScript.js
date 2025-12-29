// BIG - change this to your timezone offset
// set to GMT+0800 (Central Indonesia Time)
// NOTE - this can be negative
const timeZoneOffsetInHours = 8;

const calendarTimeoutTime = 1500;
const addToCardTimeoutTime = 3000;
const rerunScriptTimeoutTime = 7000;

// The maximum size of an amazon cart is 50
const startingCounter = 0;
const counterMax = 51;

const csvData = `
First Name,Last Name,Birthday,Email,B&G
Sam,Selig,2024-01-30,jsamselig@gmail.com,
`;

function csvToArray(str, delimiter = ",") {
  // Normalize newlines and trim leading/trailing whitespace from the entire string.
  str = str.trim().replace(/\r\n/g, "\n");

  // Split the input into lines, then extract and split the header line.
  const lines = str.split("\n");
  const headers = lines[0].split(delimiter).map((header) => header.trim());

  // Map each line to an object, using the headers for property names.
  return lines.slice(1).map((line) => {
    const values = line.split(delimiter).map((value) => value.trim());
    return headers.reduce((obj, header, index) => {
      obj[header] = values[index];
      return obj;
    }, {});
  });
}

const dataArray = csvToArray(csvData);
console.log(dataArray);
console.log(dataArray[0]);

function incrementCounter(callback) {
  chrome.storage.local.get(["counter"], function (result) {
    // Default to starting counter if undefined
    let currentCounter = result.counter || startingCounter;
    currentCounter++;
    chrome.storage.local.set({ counter: currentCounter }, function () {
      console.log("Counter value is now " + currentCounter);
      if (callback) callback(currentCounter);
    });
  });
}

function getTimestampFromBday(bdayStr, timeZoneOffsetInHours) {
  // Create a date object for April 2, 2024, at 00:00:00 in the local time zone
  const date = new Date(`${bdayStr}T00:00:00`);

  // Calculate the timezone offset for the
  // subtracting or adding the local timezone and the desired timezone
  // ie (GMT+0800) to the UTC time.
  const timeZoneOffset = timeZoneOffsetInHours * 60 * 60000; // in milliseconds
  const localOffset = date.getTimezoneOffset() * 60000; // Local timezone offset in milliseconds

  // Adjust the date to GMT+0800
  const adjustedDate = new Date(date.getTime() + timeZoneOffset + localOffset);

  // Get the timestamp in milliseconds
  const timestamp = adjustedDate.getTime();
  return timestamp;
}

/**
 * Function that opens the amazon calendar
 * to the appropriate page to allow the birthday to be pressed
 * @param {string} bdayStr
 */
function useBirthdayCalendar(bdayStr) {
  // Click the date input to open the calendar
  document.getElementById("gc-order-form-date-val").click();

  // Parse the current date and the target birthday date
  const currentDate = new Date();
  const targetDate = new Date(bdayStr);

  // Calculate the difference in months between the current date and the target date
  let monthDiff =
    (targetDate.getFullYear() - currentDate.getFullYear()) * 12 +
    targetDate.getMonth() -
    currentDate.getMonth();

  // Ensure monthDiff is non-negative
  monthDiff = Math.max(monthDiff, 0);

  // Click the next month button the required number of times
  for (let i = 0; i < monthDiff; i++) {
    document.getElementsByClassName("a-icon a-icon-next")[1].click();
  }
}

function getTimestampFromBday(bdayStr, timeZoneOffsetInHours) {
  // Create a date object for April 2, 2024, at 00:00:00 in the local time zone
  const date = new Date(`${bdayStr}T00:00:00`);

  // Calculate the timezone offset for the
  // subtracting or adding the local timezone and the desired timezone
  // ie (GMT+0800) to the UTC time.
  const timeZoneOffset = timeZoneOffsetInHours * 60 * 60000; // in milliseconds
  const localOffset = date.getTimezoneOffset() * 60000; // Local timezone offset in milliseconds

  // Adjust the date to GMT+0800
  const adjustedDate = new Date(date.getTime() + timeZoneOffset + localOffset);

  // Get the timestamp in milliseconds
  const timestamp = adjustedDate.getTime();
  return timestamp;
}

// Process and set document elements based on CSV data
function processAndSetData(i) {
  const bdayData = dataArray[i];
  document.getElementById("gc-order-form-recipients").value = bdayData.Email;

  if (bdayData["B&G"] === "X") {
    document.getElementById("gc-order-form-senderName").value =
      "Grayson & Brendan";
    document.getElementById(
      "gc-order-form-message"
    ).value = `Happy Bday ${bdayData["First Name"]} from Grayson and Brendan`;
  } else {
    document.getElementById("gc-order-form-senderName").value =
      "Brendan OBrien";
    document.getElementById(
      "gc-order-form-message"
    ).value = `Happy Bday ${bdayData["First Name"]} from Brendan O`;
  }

  useBirthdayCalendar(bdayData.Birthday);
  setTimeout(() => {
    const bdayTimestamp = getTimestampFromBday(bdayData.Birthday, 8);
    console.log(bdayTimestamp);
    document
      .getElementsByClassName(`a-cal-d a-cal-d-${bdayTimestamp}`)[0]
      .children[0].click();
    document.getElementById("gc-buy-box-atc").click();
  }, calendarTimeoutTime);
}

// Example of a function to check if an element is available
function fillFormAndSubmit() {
  console.log("Fill Out Form and Submit");
  chrome.storage.local.get(["counter"], function (result) {
    // Default to starting counter if undefined
    let counter = result.counter || startingCounter;
    console.log("Fill Out Form and Submit");
    console.log(counter);

    if (counter >= counterMax) return;

    if (!document.getElementById("gc-order-form-custom-amount")) {
      // Wait and try again
      window.location.href = "https://www.amazon.com/gp/product/B0D1TK5XVL";
      incrementCounter();
      setTimeout(fillFormAndSubmit, rerunScriptTimeoutTime);
      return;
    }

    // Your code to set values and click the button
    document.getElementById("gc-order-form-custom-amount").value = 20;

    // This series of events allows the browser to focus on the custom amount input bar.
    // This is the only way to un-click the default $50 value upon form submission
    var evt = new MouseEvent("click", {
      view: window,
      bubbles: true,
      clientX: 20,
    });
    let element = document.querySelector("#gc-order-form-custom-amount");
    element.dispatchEvent(evt);

    // Create a blur event
    var blurEvt = new FocusEvent("blur");
    // Dispatch the blur event
    element.dispatchEvent(blurEvt);

    // Then create a focus event
    var focusEvt = new FocusEvent("focus");
    // Dispatch the focus event
    element.dispatchEvent(focusEvt);

    // BIG - fill out the form
    processAndSetData(counter);

    // This adds to cart
    setTimeout(() => {
      document.getElementById("gc-buy-box-atc").click();
    }, addToCardTimeoutTime);
  });
}

// Trigger the automation when the page is loaded
fillFormAndSubmit();
