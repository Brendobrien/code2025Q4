document.getElementById('start').addEventListener('click', () => {
  console.log("Starting Automation")
  chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
    console.log("Running Script")
    chrome.scripting.executeScript({
      target: {tabId: tabs[0].id},
      files: ['contentScript.js'],
    });
  });
});