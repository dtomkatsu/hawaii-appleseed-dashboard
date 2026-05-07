import{f as w}from"./loader-xgymrUWK.js";function i(e,{isPercent:t=!1,isCurrency:r=!1,decimals:s=0}={}){if(e==null||e==="")return"N/A";try{const a=parseFloat(e);return isNaN(a)?String(e):r?"$"+a.toLocaleString("en-US",{minimumFractionDigits:s,maximumFractionDigits:s}):t?a.toFixed(1)+"%":a.toLocaleString("en-US",{minimumFractionDigits:s,maximumFractionDigits:s})}catch{return String(e)}}function y(e,t,r="state",s=!0){if(e==null||t==null||t===0)return"";try{const a=parseFloat(e),c=parseFloat(t);if(isNaN(a)||isNaN(c))return"";if(a>c){const o=a-c,l=o/c*100;return`+${s?"$"+Math.round(o).toLocaleString():Math.round(o).toLocaleString()} (+${l.toFixed(1)}%) above ${r} average`}else if(a<c){const o=c-a,l=o/c*100;return`-${s?"$"+Math.round(o).toLocaleString():Math.round(o).toLocaleString()} (${l.toFixed(1)}%) below ${r} average`}return`Same as ${r} average`}catch{return""}}function m(e,t="households"){if(!e||e<=0)return"";const r=e/100,s=[[1,2,.5],[1,3,.333],[2,3,.666],[1,4,.25],[3,4,.75],[1,5,.2],[2,5,.4],[3,5,.6],[4,5,.8],[1,6,.166],[5,6,.833],[1,7,.142],[2,7,.285],[3,7,.428],[4,7,.571],[5,7,.714],[6,7,.857],[1,8,.125],[1,9,.111]],[a,c,o]=s.reduce((f,u)=>Math.abs(r-u[2])<Math.abs(r-f[2])?u:f),l=r-o;let d="";return Math.abs(l)>=.002&&(l>0?d=l<.01?"just over ":"over ":d=l>-.01?"just under ":"under "),`${d}${a} in ${c}${t?" "+t:""}`}function b(e){if(!e)return"Unknown";let t=e;if(t.includes(", Hawaii")){const r=t.replace(" County, Hawaii","").replace(", Hawaii","");t={Honolulu:"Honolulu County",Hawaii:"Hawaiʻi County",Maui:"Maui County",Kauai:"Kauaʻi County"}[r]||`${r} County`}else/House District|Senate District/.test(t)&&(t.includes(";")&&(t=t.split(";")[0].trim()),t=t.replace(/,?\s*Hawaii/,"").replace(/\s*\(\d{4}\)\s*/g,"").trim(),t.startsWith("House District")&&(t=t.replace("House District","State House District")),t.startsWith("Senate District")&&(t=t.replace("Senate District","State Senate District")));return t}function S(e,t){const r=(t==null?void 0:t.economic)||{},s=(t==null?void 0:t.housing)||{},a=e.median_income,c=e.median_rent,o=parseFloat(e.alice_rate)||0,l=e.snap_household_rate,d=e.snap_benefits_annual_total,f=e.snap_benefit_annual_per_household,u=f?parseFloat(f)/12:0,_=u?u/30:0,g=e.rent_burden_rate,$=e.severe_rent_burden_rate;let p=e.renter_rate;if(p!=null){const v=parseFloat(p);p=v>=0&&v<=1?+(v*100).toFixed(1):+v.toFixed(1)}return{name:b(e.display_name||e.NAME||e.name),population:i(e.total_population),medianIncome:i(a,{isCurrency:!0}),incomeVsState:y(a,r.median_income,"state",!0),medianRent:i(c,{isCurrency:!0}),rentVsState:y(c,s.median_rent,"state",!0),aliceRate:i(o,{isPercent:!0}),aliceFraction:m(o,"households")||"many households",snapRate:i(l,{isPercent:!0}),snapTotal:i(d,{isCurrency:!0}),avgMonthlyBenefit:i(u,{isCurrency:!0,decimals:2}),dailyPerPerson:i(_,{isCurrency:!0,decimals:2}),ctcAvg:i(e.ctc_avg_amount,{isCurrency:!0}),ctcRate:i(e.ctc_participation_rate,{isPercent:!0}),eitcAvg:i(e.federal_eitc_avg_amount,{isCurrency:!0}),eitcRate:i(e.eitc_participation_rate,{isPercent:!0}),stateEitcAvg:i(e.state_eitc_avg_amount,{isCurrency:!0}),travelTime:i(e.travel_time_to_work_minutes,{decimals:1}),transitPct:i(e.public_transportation_pct,{isPercent:!0}),renterRate:p!=null?p+"%":"N/A",rentBurden:i(g,{isPercent:!0}),rentBurdenFraction:m(parseFloat(g)||0,"renters")||"N/A",severeRentBurden:i($,{isPercent:!0}),severeRentBurdenFraction:m(parseFloat($)||0,"renters")||"N/A",cepDisplay:e.cep_display||"N/A",cepPct:i(e.cep_percentage,{isPercent:!0}),totalSchools:e.total_schools||"N/A",cepSchools:e.cep_schools||"N/A"}}function n(e){return String(e??"").replace(/[&<>"']/g,t=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[t])}const h={bulb:'<svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M9 14a4 4 0 1 1 6 0c-.6.7-1 1.6-1 2.5V18h-4v-1.5c0-.9-.4-1.8-1-2.5z"/></svg>',dollar:'<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="12" y1="2" x2="12" y2="22"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>',utensils:'<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2"/><line x1="7" y1="2" x2="7" y2="22"/><path d="M21 15V2v0a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Z"/></svg>',bus:'<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 6v6"/><path d="M16 6v6"/><path d="M2 12h19.6"/><path d="M18 18h3s.5-1.7.8-2.8c.1-.4.2-.8.2-1.2 0-.4-.1-.8-.2-1.2l-1.4-5C20.1 6.8 19.1 6 18 6H4a2 2 0 0 0-2 2v10h3"/><circle cx="7" cy="18" r="2"/><path d="M9 18h5"/><circle cx="16" cy="18" r="2"/></svg>',home:'<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',download:'<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>'};function k(e){const t=e.name.toUpperCase();return`
    <div class="fact-sheet-container">
      <div class="fs-header">
        <img src="/hawaii-appleseed-dashboard/assets/logo.png" class="fs-logo" alt="Hawaii Appleseed" onerror="this.style.display='none'">
        <div class="fs-header-text">
          <div class="fs-kicker">Fact Sheet</div>
          <h1 class="fs-header-title">${n(e.name)}</h1>
        </div>
        <button class="fs-print-btn" onclick="window.print()">${h.download}<span>Save PDF</span></button>
      </div>

      <div class="fs-main">
        <div class="fs-did-you-know">
          <div class="fs-did-you-know-icon">${h.bulb}</div>
          <div>
            <h3>Did you know?</h3>
            <p>${n(e.aliceFraction)} (${n(e.aliceRate)}) are employed, yet struggling to make ends meet.</p>
          </div>
        </div>

        <div class="fs-stats-row">
          <div class="fs-stat-card">
            <span class="fs-stat-number">${n(e.population)}</span>
            <div class="fs-stat-label">Total Population</div>
          </div>
          <div class="fs-stat-card">
            <span class="fs-stat-number">${n(e.medianIncome)}</span>
            <div class="fs-stat-label">Median Income</div>
            <div class="fs-stat-comparison">${n(e.incomeVsState)}</div>
          </div>
          <div class="fs-stat-card">
            <span class="fs-stat-number">${n(e.medianRent)}</span>
            <div class="fs-stat-label">Median Rent</div>
            <div class="fs-stat-comparison">${n(e.rentVsState)}</div>
          </div>
        </div>

        <div class="fs-grid">
          <div class="fs-card">
            <h3><span class="fs-card-icon">${h.dollar}</span>Tax Credits</h3>
            <h4>Child Tax Credit (CTC)</h4>
            <ul>
              <li>Families receive an average of <span class="fs-hi">${n(e.ctcAvg)}</span> per year, with a participation rate of <span class="fs-hi">${n(e.ctcRate)}</span>.</li>
            </ul>
            <h4>Federal Earned Income Tax Credit (EITC)</h4>
            <ul>
              <li>Working families receive an average of <span class="fs-hi">${n(e.eitcAvg)}</span> annually, with <span class="fs-hi">${n(e.eitcRate)}</span> of eligible families participating.</li>
            </ul>
            <h4>State Earned Income Tax Credit</h4>
            <ul>
              <li>Hawaii's state EITC provides an additional <span class="fs-hi">${n(e.stateEitcAvg)}</span> on average to working families.</li>
            </ul>
          </div>

          <div class="fs-card">
            <h3><span class="fs-card-icon">${h.utensils}</span>Food Security</h3>
            <h4>SNAP</h4>
            <ul>
              <li>About <strong>${n(e.snapRate)}</strong> of households participate in SNAP.</li>
              <li>Participants receive an average of <span class="fs-hi">${n(e.avgMonthlyBenefit)}</span> per month — about <span class="fs-hi">${n(e.dailyPerPerson)}</span> per person per day.</li>
              <li>SNAP brought <span class="fs-hi">${n(e.snapTotal)}</span> in benefits to ${n(t)}.</li>
            </ul>
            <h4>School Meals (CEP)</h4>
            <ul>
              <li><strong>${n(e.cepPct)}</strong> of schools (${n(e.cepSchools)} of ${n(e.totalSchools)}) provide free meals to all students through CEP.</li>
              ${e.cepDisplay&&e.cepDisplay!=="N/A"?`<li>${n(e.cepDisplay)}</li>`:""}
            </ul>
          </div>
        </div>

        <div class="fs-grid fs-grid-second">
          <div class="fs-card">
            <h3><span class="fs-card-icon">${h.bus}</span>Transportation</h3>
            <ul>
              <li>Average travel time to work: <strong>${n(e.travelTime)} minutes</strong>.</li>
              <li><strong>${n(e.transitPct)}</strong> of workers use public transportation.</li>
              <li>Longer commutes reduce quality of life and increase costs for low-income families.</li>
            </ul>
          </div>

          <div class="fs-card">
            <h3><span class="fs-card-icon">${h.home}</span>Housing</h3>
            <ul>
              <li><strong>${n(e.renterRate)} of households</strong> are renters, with a median rent of <span class="fs-hi">${n(e.medianRent)}</span> per month.</li>
              <li><strong>${n(e.rentBurden)}</strong> of renters (${n(e.rentBurdenFraction)}) are cost-burdened, spending more than 30% of income on housing.</li>
              <li><strong>${n(e.severeRentBurden)}</strong> of renters (${n(e.severeRentBurdenFraction)}) are <em>severely</em> cost-burdened, spending more than 50%.</li>
            </ul>
          </div>
        </div>
      </div>

      <div class="fs-footer">
        <div class="fs-footer-brand">
          <img src="/hawaii-appleseed-dashboard/assets/logo.png" alt="" onerror="this.style.display='none'" style="height:28px">
          <span>HAWAIʻI APPLESEED<br><small>CENTER FOR LAW &amp; ECONOMIC JUSTICE</small></span>
        </div>
        <div class="fs-footer-url">www.hiappleseed.org/data-dashboard</div>
      </div>
    </div>`}async function C(){const e=new URLSearchParams(window.location.search),t=e.get("geo_id"),r=e.get("level")||"county",s=document.getElementById("factsheet-root");if(!t){s.innerHTML='<p class="fs-error">No geography selected. Open this page from the map by clicking a region.</p>';return}try{const[a,c]=await Promise.all([w(`/data/${r}.geojson`),w("/data/state_summary.json").catch(()=>({}))]),o=a.features.find(d=>String(d.properties.GEOID)===String(t)||String(d.properties.geoid)===String(t));if(!o){s.innerHTML=`<p class="fs-error">Geography not found: ${t}</p>`;return}const l=S(o.properties,c);document.title=`Fact Sheet: ${l.name}`,s.innerHTML=k(l)}catch(a){console.error("Fact sheet error:",a),s.innerHTML=`<p class="fs-error">Failed to load fact sheet: ${a.message}</p>`}}C();
