// (function () {
//   const script = document.currentScript;

//   const agentId =
//     script.getAttribute("data-agent-id");
  
//   const tenantId =
//     script.getAttribute("data-tenant-id");

//   const button =
//     document.createElement("button");

//   button.innerHTML = "💬";

//   button.style.position = "fixed";
//   button.style.bottom = "20px";
//   button.style.right = "20px";
//   button.style.width = "60px";
//   button.style.height = "60px";
//   button.style.borderRadius = "50%";
//   button.style.cursor = "pointer";

//   document.body.appendChild(button);

//   const iframe =
//     document.createElement("iframe");

//   iframe.src =
//     `http://192.168.1.14:3000/widget?agentId=${agentId}&tenantId=${tenantId}`;

//   iframe.style.position = "fixed";
//   iframe.style.bottom = "90px";
//   iframe.style.right = "20px";
//   iframe.style.width = "400px";
//   iframe.style.height = "400px";
//   iframe.style.display = "none";
//   iframe.style.border ="none";
//   iframe.style.background ="transparent"

//   document.body.appendChild(iframe);

//   button.onclick = () => {
//     iframe.style.display =
//       iframe.style.display === "none"
//         ? "block"
//         : "none";
//   };
// })();
(function () {
  const script = document.currentScript;

  const agentId = script.getAttribute("data-agent-id");
  const tenantId = script.getAttribute("data-tenant-id");

  // --- Chat Toggle Button ---
  const button = document.createElement("button");
  
  button.innerHTML = `
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M21 11.5C21 16.7467 16.9706 21 12 21C10.1302 21 8.39632 20.3992 6.97743 19.3722L3 20.5L4.15064 16.6329C3.41732 15.1543 3 13.4754 3 11.5C3 6.25329 7.02944 2 12 2C16.9706 2 21 6.25329 21 11.5Z" fill="#0066cc" stroke="#0066cc" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M8 10H16M8 14H14" stroke="white" stroke-width="2" stroke-linecap="round"/>
    </svg>
  `;

  button.style.position = "fixed";
  button.style.bottom = "20px";
  button.style.right = "20px";
  button.style.width = "60px";
  button.style.height = "60px";
  button.style.borderRadius = "50%";
  button.style.cursor = "pointer";
  button.style.background = "#ffffff";
  button.style.border = "1px solid #e5e5e5";
  button.style.boxShadow = "0 4px 16px rgba(0, 0, 0, 0.15)";
  button.style.display = "flex";
  button.style.alignItems = "center";
  button.style.justifyContent = "center";
  button.style.zIndex = "999999";
  button.style.transition = "transform 0.2s ease";

  button.onmouseover = () => button.style.transform = "scale(1.05)";
  button.onmouseout = () => button.style.transform = "scale(1)";

  document.body.appendChild(button);

  // --- Chat Widget Iframe ---
  const iframe = document.createElement("iframe");
//grag.gramopro.ai
  iframe.src = `http://grag.gramopro.ai/widget?agentId=${agentId}&tenantId=${tenantId}`;

  iframe.style.position = "fixed";
  iframe.style.bottom = "95px"; 
  iframe.style.right = "20px";
  iframe.style.width = "420px"; 
  iframe.style.height = "450px"; 
  iframe.style.display = "none";
  iframe.style.border = "none";
  iframe.style.background = "transparent";
  iframe.style.borderRadius = "24px";
  iframe.style.boxShadow = "0 12px 32px rgba(0, 0, 0, 0.15)";
  iframe.style.zIndex = "999999";

  document.body.appendChild(iframe);

  // Toggle Functionality
  button.onclick = () => {
    if (iframe.style.display === "none") {
      iframe.style.display = "block";
    } else {
      iframe.style.display = "none";
    }
  };
})();