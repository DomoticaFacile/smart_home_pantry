// Creato da domoticafacile.it

class SmartHomePantryCard extends HTMLElement {

  setConfig(config){ this.config = config; }

  _settings(stateObj){
    const backend = (stateObj && stateObj.attributes && stateObj.attributes.settings) || {};
    const cfg = this.config || {};
    const pick = (key, fallback) => {
      if (cfg[key] != null) return cfg[key];
      if (backend[key] != null) return backend[key];
      return fallback;
    };
    return {
      daysBefore: Number(pick("days_before", 7)),
      daysCritical: Number(pick("days_critical", 2)),
      dateFormat: String(pick("date_format", "dd/mm/yyyy")),
      nextExpiryWithin: Number(pick("next_expiry_within", 30)),
      expiredWithin: Number(pick("expired_within", 30)),
      sortOrder: String(pick("sort_order", "expiry")),
    };
  }

  _fmtDate(iso, fmt, days){
    if(!iso) return "\u2014";
    const p = iso.split("-");
    if(p.length !== 3) return iso;
    const [y, m, d] = p;
    if(fmt === "yyyy-mm-dd") return iso;
    if(fmt === "mm/dd/yyyy") return m + "/" + d + "/" + y;
    if(fmt === "relative"){
      if(days === null || days === undefined) return d + "/" + m + "/" + y;
      if(days < 0) return "Scaduto da " + Math.abs(days) + (Math.abs(days) === 1 ? " giorno" : " giorni");
      if(days === 0) return "Oggi";
      if(days === 1) return "Domani";
      return "Tra " + days + " giorni";
    }
    return d + "/" + m + "/" + y;
  }

  _s(el, styles){ for (const k in styles){ el.style[k] = styles[k]; } return el; }

  _el(tag, styles, opts){
    const e = document.createElement(tag);
    if (styles) this._s(e, styles);
    if (opts){
      if (opts.text != null) e.textContent = opts.text;
      if (opts.html != null) e.innerHTML = opts.html;
      if (opts.id) e.id = opts.id;
      if (opts.attrs) for (const a in opts.attrs) e.setAttribute(a, opts.attrs[a]);
      if (opts.on) for (const ev in opts.on) e.addEventListener(ev, opts.on[ev]);
    }
    return e;
  }

  _categoryEmoji(name){
    const n = (name || "").toLowerCase();
    const map = [
      [/latte|yogurt|formagg|mozzarell|burro|panna|ricotta/, "\ud83e\udd5b"],
      [/uov[ao]/, "\ud83e\udd5a"],
      [/pane|pang|toast|cracker|fett|brioche|croissant/, "\ud83c\udf5e"],
      [/past[ao]|spaghett|penne|maccheron|riso|farro|orzo/, "\ud83c\udf5d"],
      [/pizza/, "\ud83c\udf55"],
      [/pomodor|passata|sugo|salsa/, "\ud83c\udf45"],
      [/mel[ae]|pere|frutt|banan|arance|fragol|uva|kiwi|pesch/, "\ud83c\udf4e"],
      [/insalat|verdur|zucchin|carot|spinac|broccol|lattug/, "\ud83e\udd6c"],
      [/patat/, "\ud83e\udd54"],
      [/carne|manzo|pollo|tacchino|salsicc|wurst|prosciutt|salam|bresaol/, "\ud83c\udf56"],
      [/pesce|tonno|salmon|merluzz|gamber|acciug|sgombr/, "\ud83d\udc1f"],
      [/acqua|succo|bibit|coca|aranciat|the|caff|birra|vino/, "\ud83e\udd64"],
      [/cioccolat|biscott|merend|snack|caramell|dolc|torta|budino/, "\ud83c\udf6b"],
      [/oli[ao]|aceto/, "\ud83e\uded2"],
      [/zucchero|farina|sale|lievit|spezie/, "\ud83e\uddc2"],
      [/surgel|gelato/, "\ud83e\uddca"],
      [/detersiv|sapone|pulizi|carta|deterg/, "\ud83e\uddf4"],
    ];
    for (const [re, emo] of map){ if (re.test(n)) return emo; }
    return "\ud83d\udce6";
  }

  set hass(hass){ this._hass = hass; this._render(false); }

  _render(force){
    const hass = this._hass;
    if(!hass) return;
    const entity = (this.config && this.config.entity) || "sensor.smart_home_pantry";
    const stateObj = hass.states[entity];

    if(!this.card){
      this.card = document.createElement("ha-card");
      this.card.style.overflow = "hidden";
      this.content = document.createElement("div");
      this.card.appendChild(this.content);
      this.appendChild(this.card);
    }

    if(!stateObj){
      this.content.textContent = "Entita' non trovata";
      this._lastRenderHash = null;
      return;
    }

    const products = stateObj.attributes && stateObj.attributes.products || [];
    const S = this._settings(stateObj);
    const todayKey = new Date().toDateString();

    const renderHash = JSON.stringify([todayKey, stateObj.state, stateObj.attributes.unique_products, products, S]);
    if(!force && renderHash === this._lastRenderHash) return;
    this._lastRenderHash = renderHash;

    const today = new Date(); today.setHours(0,0,0,0);
    const daysTo = (s)=>{ if(!s) return null; const d=new Date(s+"T00:00:00"); if(isNaN(d)) return null; return Math.round((d-today)/86400000); };

    // palette
    const RED="#e53935", ORANGE="#fb8c00", GREEN="#43a047", BLUE="#1e88e5";
    const primaryText="var(--primary-text-color,#1c1c1c)";
    const secondaryText="var(--secondary-text-color,#888)";
    const cardBg="var(--card-background-color,#fff)";
    const secBg="var(--secondary-background-color,#f7f7f9)";
    const divider="var(--divider-color,#e6e6e6)";

    let expiredCount=0, expiringCount=0;
    products.forEach(p=>{
      const dd=daysTo(p.expiry_date);
      if(dd===null) return;
      if(dd<0){
        if(Math.abs(dd) <= S.expiredWithin) expiredCount+=Number(p.quantity||0);
      } else if(dd<=S.daysBefore){
        expiringCount+=Number(p.quantity||0);
      }
    });
    const totalQty = Number(stateObj.state) || 0;

    let nextExpiry=null, nextExpiryDays=null;
    products.forEach(p=>{
      const dd=daysTo(p.expiry_date);
      if(dd===null||dd<0) return;
      if(nextExpiry===null||p.expiry_date<nextExpiry){ nextExpiry=p.expiry_date; nextExpiryDays=dd; }
    });
    if(nextExpiry!==null && nextExpiryDays > S.nextExpiryWithin){ nextExpiry=null; nextExpiryDays=null; }

    this.content.textContent = "";
    this._s(this.content, {fontFamily:"var(--paper-font-body1_-_font-family,inherit)"});

    const hero = this._el("div", {background:"linear-gradient(135deg,#5b6df0 0%,#7c4dff 100%)", color:"#fff", padding:"18px 18px 22px", borderRadius:"16px 16px 0 0"});

    const h2 = this._el("h2", {margin:"0 0 14px", fontSize:"20px", fontWeight:"700", display:"flex", alignItems:"center", gap:"8px"}, {text:"\ud83d\udce6 Smart Home Pantry"});
    hero.appendChild(h2);
    const stats = this._el("div", {display:"flex", gap:"10px"});
    const mkStat=(n,l,bg)=>{
      const s=this._el("div",{flex:"1", background:bg, borderRadius:"12px", padding:"12px 8px", textAlign:"center"});
      s.appendChild(this._el("div",{fontSize:"30px",fontWeight:"800",lineHeight:"1"},{text:String(n)}));
      s.appendChild(this._el("div",{fontSize:"11px",opacity:".9",marginTop:"4px",textTransform:"uppercase",letterSpacing:".4px"},{text:l}));
      return s;
    };
    stats.appendChild(mkStat(totalQty,"Totali","rgba(255,255,255,.16)"));
    stats.appendChild(mkStat(expiringCount,"In scadenza", expiringCount>0?"rgba(251,140,0,.35)":"rgba(255,255,255,.16)"));
    stats.appendChild(mkStat(expiredCount,"Scaduti", expiredCount>0?"rgba(229,57,53,.4)":"rgba(255,255,255,.16)"));
    hero.appendChild(stats);

    if(nextExpiry){
      const dd = nextExpiryDays;
      let testo;
      if(S.dateFormat === "relative"){

        testo = "\u23f3 Prossima scadenza: " + this._fmtDate(nextExpiry, "relative", dd).toLowerCase();
      } else {
        let when="";
        if(dd===0) when=" (oggi)";
        else if(dd===1) when=" (domani)";
        else if(dd>1) when=" (tra "+dd+" giorni)";
        testo = "\u23f3 Prossima scadenza: " + this._fmtDate(nextExpiry, S.dateFormat, dd) + when;
      }
      const nextRow=this._el("div",{
        marginTop:"12px",
        padding:"8px 12px",
        background:"rgba(255,255,255,.14)",
        borderRadius:"10px",
        fontSize:"13px",
        display:"flex",
        alignItems:"center",
        gap:"6px"
      },{text:testo});
      hero.appendChild(nextRow);
    }

    if(expiredCount > 0){
      const expRow=this._el("div",{
        marginTop:"8px",
        padding:"8px 12px",
        background:"rgba(229,57,53,.35)",
        borderRadius:"10px",
        fontSize:"13px",
        display:"flex",
        alignItems:"center",
        flexWrap:"wrap",
        gap:"8px"
      });
      const label = expiredCount === 1
        ? "1 prodotto scaduto"
        : expiredCount + " prodotti scaduti";
      expRow.appendChild(this._el("div",{flex:"1",minWidth:"120px",fontWeight:"600"},{text:"\u26d4 "+label}));

      const miniBtn=(text,bg)=>this._el("button",{
        padding:"5px 10px",
        border:"none",
        borderRadius:"8px",
        fontSize:"12px",
        fontWeight:"700",
        cursor:"pointer",
        color:"#fff",
        background:bg,
        flex:"0 0 auto"
      },{text:text});

      const btnXlsx=miniBtn("\ud83d\udcca Excel","rgba(255,255,255,.28)");
      btnXlsx.addEventListener("click",()=>this._downloadExpired(btnXlsx));
      expRow.appendChild(btnXlsx);

      const btnClear=miniBtn("\ud83e\uddf9 Azzera","rgba(0,0,0,.35)");
      btnClear.addEventListener("click",()=>this._clearExpired(expiredCount, btnClear));
      expRow.appendChild(btnClear);

      hero.appendChild(expRow);
    }

    this.content.appendChild(hero);

    const body = this._el("div", {padding:"14px"});
    this.content.appendChild(body);

    const grouped={};
    products.forEach(p=>{ const key=p.barcode||p.name; if(!grouped[key]) grouped[key]={name:p.name,total:0,lots:[]}; grouped[key].total+=Number(p.quantity||0); grouped[key].lots.push(p); });
    const groups=Object.values(grouped).filter(g=>g.total>0);

    const FAR = "9999-12-31";
    groups.forEach(g=>{
      let first = null;
      g.lots.forEach(l=>{
        if(!l.expiry_date) return;
        if(first === null || l.expiry_date < first) first = l.expiry_date;
      });
      g._next = first;
      g._nextDays = daysTo(first);
    });
    const byName = (a,b)=>String(a.name||"").localeCompare(String(b.name||""), "it", {sensitivity:"base"});
    const byExpiry = (a,b)=>{

      const cmp = (a._next || FAR).localeCompare(b._next || FAR);
      return cmp !== 0 ? cmp : byName(a,b);
    };
    const sorters = {

      expiry: byExpiry,

      expiry_valid: (a,b)=>{
        const aExp = a._nextDays !== null && a._nextDays < 0;
        const bExp = b._nextDays !== null && b._nextDays < 0;
        if(aExp !== bExp) return aExp ? 1 : -1;
        return byExpiry(a,b);
      },
      alphabetical: byName,

      quantity_asc: (a,b)=> (a.total - b.total) || byName(a,b),

      quantity_desc: (a,b)=> (b.total - a.total) || byName(a,b),
    };
    groups.sort(sorters[S.sortOrder] || sorters.expiry);

    if(groups.length===0){
      body.appendChild(this._el("div",{textAlign:"center",color:secondaryText,padding:"26px 10px",fontSize:"15px"},{html:"\ud83e\uded9 La dispensa e' vuota.<br>Tocca <b>Aggiungi</b> per scansionare un prodotto."}));
    }

    groups.forEach(g=>{
      const grp=this._el("div",{background:cardBg,border:"1px solid "+divider,borderRadius:"14px",marginBottom:"10px",overflow:"hidden",boxShadow:"0 1px 3px rgba(0,0,0,.06)"});
      const hd=this._el("div",{display:"flex",alignItems:"center",gap:"12px",padding:"12px 14px",background:secBg});
      hd.appendChild(this._el("div",{fontSize:"26px",width:"40px",height:"40px",display:"flex",alignItems:"center",justifyContent:"center",background:cardBg,borderRadius:"10px",boxShadow:"0 1px 2px rgba(0,0,0,.12)",flex:"0 0 auto"},{text:this._categoryEmoji(g.name)}));
      hd.appendChild(this._el("div",{fontWeight:"700",fontSize:"15px",color:primaryText,flex:"1",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"},{text:g.name||"Senza nome"}));
      hd.appendChild(this._el("div",{fontSize:"13px",fontWeight:"800",color:"#fff",background:BLUE,borderRadius:"999px",padding:"3px 10px",flex:"0 0 auto"},{text:String(g.total)}));
      grp.appendChild(hd);

      const lots=this._el("div",{padding:"6px 10px 10px"});
      g.lots.slice().sort((a,b)=>(a.expiry_date||"9999-12-31").localeCompare(b.expiry_date||"9999-12-31")).forEach(l=>{
        const dd=daysTo(l.expiry_date);
        let barColor=GREEN, subColor=secondaryText, sub="Nessuna scadenza";
        if(dd!==null){
          if(dd<0){
            barColor=RED; subColor=RED;
            sub="Scaduto da "+Math.abs(dd)+" "+(Math.abs(dd)===1?"giorno":"giorni");
          } else if(dd===0){
            barColor=RED; subColor=RED;
            sub="Scade oggi!";
          } else if(dd<=S.daysCritical){

            barColor=RED; subColor=RED;
            sub="Scade tra "+dd+" "+(dd===1?"giorno":"giorni")+"!";
          } else if(dd<=S.daysBefore){

            barColor=ORANGE; subColor=ORANGE;
            sub="Scade tra "+dd+" "+(dd===1?"giorno":"giorni");
          } else {
            sub="Scade il "+this._fmtDate(l.expiry_date, S.dateFormat, dd);
          }
        }
        const row=this._el("div",{display:"flex",alignItems:"center",gap:"10px",padding:"9px 10px",borderRadius:"10px"});
        if(l.barcode){
          row.style.cursor="pointer";
          row.addEventListener("click",()=>this._openEditLotModal({barcode:l.barcode,name:l.name,expiry:l.expiry_date||null,quantity:Number(l.quantity||0)}));
        }
        row.appendChild(this._el("div",{width:"5px",alignSelf:"stretch",borderRadius:"3px",background:barColor,flex:"0 0 auto"}));
        const main=this._el("div",{flex:"1",minWidth:"0"});
        main.appendChild(this._el("div",{fontSize:"14px",color:primaryText,fontWeight:"600"},{text:"\ud83d\udcc5 "+this._fmtDate(l.expiry_date, S.dateFormat, dd)}));
        main.appendChild(this._el("div",{fontSize:"12px",marginTop:"1px",color:subColor},{text:sub}));
        row.appendChild(main);
        row.appendChild(this._el("div",{fontSize:"15px",fontWeight:"800",color:primaryText,flex:"0 0 auto"},{text:"\u00d7"+l.quantity}));
        if(l.barcode) row.appendChild(this._el("div",{opacity:".4",fontSize:"14px",flex:"0 0 auto"},{text:"\u270f\ufe0f"}));
        lots.appendChild(row);
      });
      grp.appendChild(lots);
      body.appendChild(grp);
    });

    const actions=this._el("div",{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(120px,1fr))",gap:"8px",marginTop:"6px"});
    const mkBtn=(id,label,grad)=>{
      const b=this._el("button",{display:"flex",alignItems:"center",justifyContent:"center",gap:"6px",padding:"11px 10px",border:"none",borderRadius:"12px",fontSize:"14px",fontWeight:"700",cursor:"pointer",color:"#fff",background:grad},{id:id,text:label});
      return b;
    };
    const bAdd=mkBtn("scanBtn","\ud83d\udcf7 Aggiungi","linear-gradient(135deg,#43a047,#2e7d32)");
    const bTake=mkBtn("removeScanBtn","\ud83d\udce4 Preleva","linear-gradient(135deg,#1e88e5,#1565c0)");
    const bRem=mkBtn("manualRemoveBtn","\u2796 Rimuovi","linear-gradient(135deg,#fb8c00,#ef6c00)");
    const bRef=mkBtn("refreshBtn","\ud83d\udd04 Aggiorna","linear-gradient(135deg,#8e24aa,#6a1b9a)");
    const bClr=mkBtn("clearBtn","\ud83d\uddd1\ufe0f Svuota","linear-gradient(135deg,#e53935,#c62828)");
    actions.appendChild(bAdd); actions.appendChild(bTake); actions.appendChild(bRem); actions.appendChild(bRef); actions.appendChild(bClr);
    body.appendChild(actions);

    bRef.addEventListener("click", async (ev)=>{
      const btn=ev.currentTarget; btn.disabled=true; btn.textContent="\u23f3 Aggiorno...";
      try{
        await this._hass.callService("smart_home_pantry","refresh",{});
        this.dispatchEvent(new CustomEvent("hass-notification",{detail:{message:"Dispensa aggiornata"},bubbles:true,composed:true}));
      }catch(err){ console.error(err); alert("Errore durante l'aggiornamento"); }
      finally{ this._render(true); }
    });

    bClr.addEventListener("click", async ()=>{
      const conf=prompt("Digita SVUOTA per confermare");
      if(conf!=="SVUOTA") return;
      try{ await this._hass.callService("smart_home_pantry","clear_pantry",{}); alert("Dispensa svuotata"); this._render(true); }
      catch(err){ console.error(err); alert("Errore durante lo svuotamento"); }
    });

    bRem.addEventListener("click", ()=>this._openManualRemove(stateObj));
    bTake.addEventListener("click", ()=>this._openScanner("remove"));
    bAdd.addEventListener("click", ()=>this._openScanner("add"));
  }

  _openScanner(mode){
    const overlay=this._el("div",{position:"fixed",inset:"0",background:"black",zIndex:"9999"});
    const reader=this._el("div",{width:"100%",height:"90%"},{id:mode==="add"?"reader":"reader_remove"});
    const closeBtn=this._el("button",{position:"absolute",top:"10px",right:"10px",fontSize:"20px"},{text:"\u2716"});
    overlay.appendChild(reader); overlay.appendChild(closeBtn);
    document.body.appendChild(overlay);
    const loadLib=()=>new Promise((resolve,reject)=>{ if(window.Html5Qrcode){resolve();return;} const s=document.createElement('script'); s.src='https://unpkg.com/html5-qrcode'; s.onload=resolve; s.onerror=reject; document.head.appendChild(s); });
    const done = mode==="add" ? "__shp_scan_done" : "__shp_remove_done";
    (async ()=>{
      try{
        await loadLib();
        window[done]=false;
        const qr=new Html5Qrcode(reader.id);
        await qr.start({facingMode:"environment"},{fps:10,qrbox:250}, async(decodedText)=>{
          if(window[done]) return; window[done]=true;
          try{await qr.stop();}catch(e){}
          overlay.remove();
          if(mode==="add"){ await this._handleScannedBarcode(decodedText); }
          else {
            const qtyStr=prompt("Prodotto rilevato: "+decodedText+"\n\nQuanti pezzi vuoi rimuovere?","1");
            const qty=Math.max(1,parseInt(qtyStr||"1",10)||1);
            await this._hass.callService("smart_home_pantry","remove_quantity",{barcode:decodedText,quantity:qty});
            alert("Rimossi "+qty+" pezzi");
          }
        });
        closeBtn.onclick=async()=>{try{await qr.stop();}catch(e){} overlay.remove();};
      }catch(e){
        overlay.remove();
        const barcode=prompt(mode==="add"?"Scanner non disponibile. Inserisci barcode":"Barcode da rimuovere");
        if(!barcode) return;
        if(mode==="add"){ await this._handleScannedBarcode(barcode); }
        else { const qtyStr=prompt("Quanti pezzi vuoi rimuovere?","1"); const qty=Math.max(1,parseInt(qtyStr||"1",10)||1); await this._hass.callService("smart_home_pantry","remove_quantity",{barcode,quantity:qty}); }
      }
    })();
  }

  async _lookupBarcode(barcode){
    const entity=(this.config&&this.config.entity)||"sensor.smart_home_pantry";
    const requestId="req_"+Date.now()+"_"+Math.floor(Math.random()*100000);
    await this._hass.callService("smart_home_pantry","lookup_barcode",{barcode:barcode,request_id:requestId});
    const deadline=Date.now()+12000;
    while(Date.now()<deadline){
      const st=this._hass.states[entity];
      const lk=st&&st.attributes?st.attributes.lookup:null;
      if(lk&&lk.request_id===requestId) return lk;
      await new Promise(r=>setTimeout(r,250));
    }
    return null;
  }

  async _handleScannedBarcode(barcode){
    barcode=String(barcode||"").trim();
    if(!barcode) return;
    const wait=this._el("div",{position:"fixed",inset:"0",background:"rgba(0,0,0,.4)",zIndex:"10000",display:"flex",alignItems:"center",justifyContent:"center",color:"#fff",fontSize:"18px"},{text:"\ud83d\udd0e Cerco il prodotto..."});
    document.body.appendChild(wait);
    let lookup=null;
    try{ lookup=await this._lookupBarcode(barcode); }catch(e){ console.error(e); }
    wait.remove();
    const foundName=(lookup&&lookup.found&&lookup.name)?lookup.name:"";
    this._openAddModal(barcode,foundName);
  }

  _overlay(){
    return this._el("div",{position:"fixed",inset:"0",background:"rgba(0,0,0,.6)",zIndex:"10001",display:"flex",alignItems:"center",justifyContent:"center",padding:"16px"});
  }
  _modalBox(maxW){
    return this._el("div",{background:"#fff",color:"#1c1c1c",borderRadius:"12px",width:"100%",maxWidth:maxW||"440px",overflow:"hidden",boxShadow:"0 8px 30px rgba(0,0,0,.3)"});
  }
  _modalHeader(title, onClose){
    const hd=this._el("div",{padding:"16px",borderBottom:"1px solid #eee",display:"flex",alignItems:"center",justifyContent:"space-between"});
    hd.appendChild(this._el("h3",{margin:"0",color:"#1c1c1c",fontSize:"18px"},{text:title}));
    hd.appendChild(this._el("button",{background:"none",border:"none",fontSize:"20px",color:"#333",cursor:"pointer"},{text:"\u2716",on:{click:onClose}}));
    return hd;
  }
  _label(text){ return this._el("label",{display:"block",fontSize:"13px",color:"#555",marginBottom:"4px"},{html:text}); }
  _input(opts){
    const i=this._el("input",{fontSize:"16px",height:"36px",color:"#1c1c1c",background:"#fff",border:"1px solid #ccc",borderRadius:"6px",padding:"0 8px",boxSizing:"border-box"});
    if(opts){ if(opts.type)i.type=opts.type; if(opts.value!=null)i.value=opts.value; if(opts.id)i.id=opts.id; if(opts.placeholder)i.placeholder=opts.placeholder; if(opts.readonly){i.readOnly=true;i.style.background="#f4f4f4";i.style.color="#444";} if(opts.width)i.style.width=opts.width; if(opts.min!=null)i.min=opts.min; if(opts.max!=null)i.max=opts.max; if(opts.textAlign)i.style.textAlign=opts.textAlign; if(opts.marginBottom)i.style.marginBottom=opts.marginBottom; if(opts.flex)i.style.flex=opts.flex; if(opts.borderColor)i.style.borderColor=opts.borderColor; }
    return i;
  }
  _btn(text, kind){
    const styles={height:"38px",padding:"0 16px",borderRadius:"6px",cursor:"pointer",fontSize:"15px",border:"1px solid #ccc",background:"#e9e9e9",color:"#1c1c1c"};
    if(kind==="green"){styles.background="#2e7d32";styles.color="#fff";styles.border="none";styles.fontWeight="bold";}
    if(kind==="blue"){styles.background="#1976d2";styles.color="#fff";styles.border="none";styles.fontWeight="bold";}
    if(kind==="red"){styles.background="#d32f2f";styles.color="#fff";styles.border="none";styles.fontWeight="bold";}
    return this._el("button",styles,{text:text});
  }
  _smallBtn(text){ return this._el("button",{width:"36px",height:"36px",fontSize:"18px",borderRadius:"6px",border:"1px solid #ccc",background:"#e9e9e9",color:"#1c1c1c",cursor:"pointer"},{text:text}); }

  _openAddModal(barcode, foundName){
    const notFound=!foundName;
    const ov=this._overlay();
    const box=this._modalBox("440px");
    const close=()=>ov.remove();
    box.appendChild(this._modalHeader("\ud83d\udcf7 Aggiungi prodotto", close));
    const bodyM=this._el("div",{padding:"16px"});

    bodyM.appendChild(this._label("Codice a barre"));
    const barInp=this._input({type:"text",value:barcode,readonly:true,width:"100%",marginBottom:"14px"});
    bodyM.appendChild(barInp);

    bodyM.appendChild(this._label("Nome prodotto"+(notFound?' <span style="color:#ef6c00">(non trovato, scrivilo tu)</span>':'')));
    const nameInp=this._input({type:"text",value:foundName,placeholder:"Es. Latte parzialmente scremato",width:"100%",marginBottom:"14px",borderColor:notFound?"#ef6c00":"#ccc"});
    bodyM.appendChild(nameInp);

    bodyM.appendChild(this._label("Quantita'"));
    const qtyRow=this._el("div",{display:"flex",alignItems:"center",gap:"8px",marginBottom:"14px"});
    const minus=this._smallBtn("\u2212"), plus=this._smallBtn("+");
    const qtyInp=this._input({type:"number",min:1,value:1,textAlign:"center",width:"70px"});
    minus.onclick=()=>qtyInp.value=Math.max(1,(parseInt(qtyInp.value,10)||1)-1);
    plus.onclick=()=>qtyInp.value=Math.max(1,(parseInt(qtyInp.value,10)||1)+1);
    qtyRow.appendChild(minus); qtyRow.appendChild(qtyInp); qtyRow.appendChild(plus);
    bodyM.appendChild(qtyRow);

    bodyM.appendChild(this._label("Data di scadenza"));
    const expRow=this._el("div",{display:"flex",alignItems:"center",gap:"8px",marginBottom:"20px"});
    const expInp=this._input({type:"date",flex:"1"});
    const noDate=this._el("button",{height:"36px",padding:"0 10px",borderRadius:"6px",border:"1px solid #ccc",background:"#e9e9e9",color:"#1c1c1c",cursor:"pointer"},{text:"Nessuna",on:{click:()=>expInp.value=""}});
    expRow.appendChild(expInp); expRow.appendChild(noDate);
    bodyM.appendChild(expRow);

    const btnRow=this._el("div",{display:"flex",justifyContent:"flex-end",gap:"8px"});
    const cancel=this._btn("Annulla"); cancel.onclick=close;
    const save=this._btn("Aggiungi","green");
    btnRow.appendChild(cancel); btnRow.appendChild(save);
    bodyM.appendChild(btnRow);

    box.appendChild(bodyM); ov.appendChild(box); document.body.appendChild(ov);
    ov.addEventListener("click",(e)=>{ if(e.target===ov) close(); });
    if(notFound) setTimeout(()=>nameInp.focus(),50);

    save.onclick=async()=>{
      const name=nameInp.value.trim();
      if(!name){ alert("Inserisci un nome per il prodotto."); nameInp.focus(); return; }
      let qty=parseInt(qtyInp.value,10); if(isNaN(qty)||qty<1) qty=1;
      const expiry=expInp.value||null;
      save.disabled=true; save.textContent="...";
      try{
        for(let i=0;i<qty;i++){ await this._hass.callService("smart_home_pantry","add_product",{barcode:barcode,name:name,expiry_date:expiry}); }
        this.dispatchEvent(new CustomEvent("hass-notification",{detail:{message:"Aggiunti "+qty+" \u00d7 "+name},bubbles:true,composed:true}));
        close();
      }catch(err){ console.error(err); alert("Errore durante l'aggiunta"); save.disabled=false; save.textContent="Aggiungi"; }
    };
  }

  _openEditLotModal(lot){
    const ov=this._overlay();
    const box=this._modalBox("420px");
    const close=()=>ov.remove();
    box.appendChild(this._modalHeader("\u270f\ufe0f Modifica lotto", close));
    const bodyM=this._el("div",{padding:"16px"});
    bodyM.appendChild(this._el("div",{fontWeight:"bold",color:"#1c1c1c",marginBottom:"12px"},{text:lot.name||lot.barcode}));

    bodyM.appendChild(this._label("Quantita'"));
    const qtyRow=this._el("div",{display:"flex",alignItems:"center",gap:"8px",marginBottom:"16px"});
    const minus=this._smallBtn("\u2212"), plus=this._smallBtn("+");
    const qtyInp=this._input({type:"number",min:0,value:lot.quantity,textAlign:"center",width:"70px"});
    minus.onclick=()=>qtyInp.value=Math.max(0,(parseInt(qtyInp.value,10)||0)-1);
    plus.onclick=()=>qtyInp.value=Math.max(0,(parseInt(qtyInp.value,10)||0)+1);
    qtyRow.appendChild(minus); qtyRow.appendChild(qtyInp); qtyRow.appendChild(plus);
    qtyRow.appendChild(this._el("span",{fontSize:"12px",color:"#777"},{text:"(0 = rimuovi lotto)"}));
    bodyM.appendChild(qtyRow);

    bodyM.appendChild(this._label("Data di scadenza"));
    const expRow=this._el("div",{display:"flex",alignItems:"center",gap:"8px",marginBottom:"20px"});
    const expInp=this._input({type:"date",value:lot.expiry||"",flex:"1"});
    const noDate=this._el("button",{height:"36px",padding:"0 10px",borderRadius:"6px",border:"1px solid #ccc",background:"#e9e9e9",color:"#1c1c1c",cursor:"pointer"},{text:"Nessuna",on:{click:()=>expInp.value=""}});
    expRow.appendChild(expInp); expRow.appendChild(noDate);
    bodyM.appendChild(expRow);

    const btnRow=this._el("div",{display:"flex",justifyContent:"flex-end",gap:"8px"});
    const cancel=this._btn("Annulla"); cancel.onclick=close;
    const save=this._btn("Salva","blue");
    btnRow.appendChild(cancel); btnRow.appendChild(save);
    bodyM.appendChild(btnRow);

    box.appendChild(bodyM); ov.appendChild(box); document.body.appendChild(ov);
    ov.addEventListener("click",(e)=>{ if(e.target===ov) close(); });

    save.onclick=async()=>{
      let newQty=parseInt(qtyInp.value,10); if(isNaN(newQty)||newQty<0) newQty=lot.quantity;
      const newExpiry=expInp.value||null;
      const qtyChanged=newQty!==lot.quantity;
      const expiryChanged=newExpiry!==(lot.expiry||null);
      if(!qtyChanged&&!expiryChanged){ close(); return; }
      if(newQty===0&&!confirm("Rimuovere completamente questo lotto di "+(lot.name||lot.barcode)+"?")) return;
      const payload={barcode:lot.barcode,old_expiry_date:lot.expiry||""};
      if(qtyChanged) payload.quantity=newQty;
      if(expiryChanged) payload.new_expiry_date=newExpiry||"";
      save.disabled=true; save.textContent="...";
      try{
        await this._hass.callService("smart_home_pantry","update_lot",payload);
        this.dispatchEvent(new CustomEvent("hass-notification",{detail:{message:"Lotto aggiornato"},bubbles:true,composed:true}));
        close();
      }catch(err){ console.error(err); alert("Errore durante la modifica"); save.disabled=false; save.textContent="Salva"; }
    };
  }

  _openManualRemove(stateObj){
    const groups={};
    (stateObj.attributes&&stateObj.attributes.products||[]).forEach(p=>{
      const key=p.barcode||p.name;
      if(!groups[key]) groups[key]={key,barcode:p.barcode,name:p.name,total:0,next:null};
      groups[key].total+=Number(p.quantity||0);
      const e=p.expiry_date;
      if(e&&(groups[key].next===null||e<groups[key].next)) groups[key].next=e;
    });
    const list=Object.values(groups).filter(g=>g.total>0);
    if(list.length===0){ alert("La dispensa e' vuota, niente da rimuovere."); return; }
    list.sort((a,b)=>(a.next||"9999-12-31").localeCompare(b.next||"9999-12-31")||(a.name||"").localeCompare(b.name||""));

    const ov=this._overlay();
    const box=this._modalBox("520px");
    this._s(box,{maxHeight:"80vh",display:"flex",flexDirection:"column"});
    const close=()=>ov.remove();
    box.appendChild(this._modalHeader("\u2796 Rimozione manuale", close));
    box.appendChild(this._el("div",{fontSize:"12px",color:"#777",padding:"8px 16px 0"},{text:"I pezzi vengono tolti dal lotto che scade prima (FEFO)."}));
    const listWrap=this._el("div",{overflowY:"auto",padding:"8px 16px 16px"});

    list.forEach(g=>{
      const row=this._el("div",{display:"flex",alignItems:"center",justifyContent:"space-between",gap:"8px",padding:"10px",borderBottom:"1px solid #eee"});
      const info=this._el("div",{});
      info.appendChild(this._el("div",{fontWeight:"bold",color:"#1c1c1c"},{text:g.name||g.barcode}));
      info.appendChild(this._el("div",{fontSize:"12px",color:"#777"},{text:"Disponibili: "+g.total+(g.next?" \u00b7 prima scadenza: "+g.next:"")}));
      row.appendChild(info);
      const ctrl=this._el("div",{display:"flex",alignItems:"center",gap:"6px"});
      const minus=this._el("button",{width:"32px",height:"32px",fontSize:"18px",borderRadius:"6px",border:"1px solid #ccc",background:"#e9e9e9",color:"#1c1c1c",cursor:"pointer"},{text:"\u2212"});
      const qtyInp=this._input({type:"number",min:1,max:g.total,value:1,textAlign:"center",width:"52px"});
      const plus=this._el("button",{width:"32px",height:"32px",fontSize:"18px",borderRadius:"6px",border:"1px solid #ccc",background:"#e9e9e9",color:"#1c1c1c",cursor:"pointer"},{text:"+"});
      const remBtn=this._el("button",{height:"34px",padding:"0 10px",borderRadius:"6px",border:"none",background:"#d32f2f",color:"#fff",fontWeight:"bold",cursor:"pointer"},{text:"Rimuovi"});
      const clamp=()=>{ let v=parseInt(qtyInp.value,10); if(isNaN(v)||v<1)v=1; if(v>g.total)v=g.total; qtyInp.value=v; return v; };
      minus.onclick=()=>qtyInp.value=Math.max(1,(parseInt(qtyInp.value,10)||1)-1);
      plus.onclick=()=>qtyInp.value=Math.min(g.total,(parseInt(qtyInp.value,10)||1)+1);
      qtyInp.onchange=clamp;
      remBtn.onclick=async()=>{
        const qty=clamp();
        if(!g.barcode){ alert("Questo prodotto non ha codice a barre: non rimovibile da qui."); return; }
        if(!confirm("Rimuovere "+qty+" \u00d7 "+(g.name||g.barcode)+"?")) return;
        remBtn.disabled=true; remBtn.textContent="...";
        try{
          await this._hass.callService("smart_home_pantry","remove_quantity",{barcode:g.barcode,quantity:qty});
          this.dispatchEvent(new CustomEvent("hass-notification",{detail:{message:"Rimossi "+qty+" \u00d7 "+(g.name||g.barcode)},bubbles:true,composed:true}));
          close();
        }catch(err){ console.error(err); alert("Errore durante la rimozione"); remBtn.disabled=false; remBtn.textContent="Rimuovi"; }
      };
      ctrl.appendChild(minus); ctrl.appendChild(qtyInp); ctrl.appendChild(plus); ctrl.appendChild(remBtn);
      row.appendChild(ctrl);
      listWrap.appendChild(row);
    });

    box.appendChild(listWrap); ov.appendChild(box); document.body.appendChild(ov);
    ov.addEventListener("click",(e)=>{ if(e.target===ov) close(); });
  }

  async _downloadExpired(btn){
    const originale = btn ? btn.textContent : null;
    if(btn){ btn.disabled = true; btn.textContent = "..."; }
    try{
      const signed = await this._hass.callWS({
        type: "auth/sign_path",
        path: "/smart_home_pantry/export_expired.xlsx",
        expires: 60
      });
      const a = document.createElement("a");
      a.href = signed.path;
      a.download = "prodotti_scaduti.xlsx";
      document.body.appendChild(a);
      a.click();
      a.remove();
    }catch(err){
      console.error("Download export fallito", err);
      alert("Non e' stato possibile scaricare il file.");
    }finally{
      if(btn){ btn.disabled = false; btn.textContent = originale; }
    }
  }

  async _clearExpired(count, btn){
    const quanti = count === 1 ? "1 prodotto scaduto" : count + " prodotti scaduti";
    if(!confirm("Rimuovere " + quanti + " dalla dispensa?\n\nL'operazione non e' reversibile: se ti serve la lista, scaricala prima in Excel.")) return;
    const originale = btn ? btn.textContent : null;
    if(btn){ btn.disabled = true; btn.textContent = "..."; }
    try{
      await this._hass.callService("smart_home_pantry", "clear_expired", {});
      this.dispatchEvent(new CustomEvent("hass-notification",{
        detail:{message:"Prodotti scaduti rimossi"},
        bubbles:true, composed:true
      }));
      this._render(true);
    }catch(err){
      console.error("clear_expired fallito", err);
      alert("Errore durante la rimozione dei prodotti scaduti.");
      if(btn){ btn.disabled = false; btn.textContent = originale; }
    }
  }

  getCardSize(){ return 4; }
}

if(!customElements.get("smart-home-pantry-card")){
  customElements.define("smart-home-pantry-card", SmartHomePantryCard);
}
