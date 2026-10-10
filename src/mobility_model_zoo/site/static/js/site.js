// Conveniences of the zoo website (feature 008). Every page is complete without this file:
// it only adds copy buttons and links a marked quote with its JSON item. Nothing is stored.
(function () {
  "use strict";
  document.documentElement.classList.add("js");

  document.addEventListener("click", function (event) {
    var button = event.target.closest("button.copy");
    if (button) {
      var source = document.getElementById(button.getAttribute("data-copy"));
      if (!source || !navigator.clipboard) return;
      navigator.clipboard.writeText(source.textContent).then(function () {
        var label = button.textContent;
        button.textContent = "Copied";
        button.setAttribute("aria-live", "polite");
        setTimeout(function () { button.textContent = label; }, 1600);
      });
      return;
    }
    var link = event.target.closest("a[data-pair]");
    if (!link) return;
    var partner = document.getElementById(link.getAttribute("data-pair"));
    if (!partner) return;
    event.preventDefault();
    var example = link.closest(".example");
    example.querySelectorAll(".sel").forEach(function (el) {
      el.classList.remove("sel");
      el.removeAttribute("aria-current");
    });
    [link, partner].forEach(function (el) {
      el.classList.add("sel");
      el.setAttribute("aria-current", "true");
    });
    partner.scrollIntoView({ block: "nearest" });
  });
})();
