// Creato da domoticafacile.it

import "./smart-home-pantry-card.js";

class SmartHomePantryPanel extends HTMLElement {

  _el(tag, styles, opts){
    const e = document.createElement(tag);
    if(styles){ for(const k in styles){ e.style[k] = styles[k]; } }
    if(opts){
      if(opts.text != null) e.textContent = opts.text;
      if(opts.on) for(const ev in opts.on) e.addEventListener(ev, opts.on[ev]);
    }
    return e;
  }

  set hass(hass){
    this._hass = hass;
    this._build();
    if(this._card) this._card.hass = hass;
  }

  set narrow(narrow){
    this._narrow = narrow;
    this._syncHeader();
  }

  set panel(panel){
    this._panel = panel;
    this._syncHeader();
  }

  get _title(){
    if(this._panel && this._panel.title) return this._panel.title;
    return "Smart Home Pantry";
  }

  _syncHeader(){
    if(this._titleEl) this._titleEl.textContent = this._title;
    if(this._menuBtn) this._menuBtn.style.display = this._narrow ? "block" : "none";
  }

  _build(){
    if(this._built) return;
    this._built = true;

    this.style.display = "block";
    this.style.height = "100%";
    this.style.background = "var(--primary-background-color, #f5f5f5)";

    const header = this._el("div", {
      display: "flex",
      alignItems: "center",
      gap: "12px",
      height: "56px",
      padding: "0 16px",
      background: "var(--app-header-background-color, var(--primary-color, #03a9f4))",
      color: "var(--app-header-text-color, #fff)",
      boxSizing: "border-box"
    });

    this._menuBtn = this._el("button", {
      display: "none",
      background: "none",
      border: "none",
      color: "inherit",
      fontSize: "22px",
      cursor: "pointer",
      padding: "0",
      lineHeight: "1"
    }, {
      text: "\u2630",
      on: {
        click: () => {
          this.dispatchEvent(new CustomEvent("hass-toggle-menu", {
            bubbles: true,
            composed: true
          }));
        }
      }
    });
    header.appendChild(this._menuBtn);

    this._titleEl = this._el("div", {
      fontSize: "20px",
      fontWeight: "600"
    }, { text: this._title });
    header.appendChild(this._titleEl);

    this.appendChild(header);

    const wrap = this._el("div", {
      padding: "16px",
      display: "flex",
      justifyContent: "center",
      boxSizing: "border-box"
    });
    const inner = this._el("div", {
      width: "100%",
      maxWidth: "600px"
    });

    this._card = document.createElement("smart-home-pantry-card");
    this._card.setConfig(this._cardConfig());
    inner.appendChild(this._card);
    wrap.appendChild(inner);
    this.appendChild(wrap);

    this._syncHeader();
  }

  _cardConfig(){

    if(this._panel && this._panel.config && this._panel.config.card){
      return this._panel.config.card;
    }
    return {};
  }
}

if(!customElements.get("smart-home-pantry-panel")){
  customElements.define("smart-home-pantry-panel", SmartHomePantryPanel);
}
