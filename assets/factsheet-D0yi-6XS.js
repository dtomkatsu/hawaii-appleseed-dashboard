import{f as $}from"./loader-xgymrUWK.js";function i(e,{isPercent:t=!1,isCurrency:s=!1,decimals:r=0}={}){if(e==null||e==="")return"N/A";try{const n=parseFloat(e);return isNaN(n)?String(e):s?"$"+n.toLocaleString("en-US",{minimumFractionDigits:r,maximumFractionDigits:r}):t?n.toFixed(1)+"%":n.toLocaleString("en-US",{minimumFractionDigits:r,maximumFractionDigits:r})}catch{return String(e)}}function _(e,t,s="state",r=!0){if(e==null||t==null||t===0)return"";try{const n=parseFloat(e),c=parseFloat(t);if(isNaN(n)||isNaN(c))return"";if(n>c){const o=n-c,l=o/c*100;return`+${r?"$"+Math.round(o).toLocaleString():Math.round(o).toLocaleString()} (+${l.toFixed(1)}%) above ${s} average`}else if(n<c){const o=c-n,l=o/c*100;return`-${r?"$"+Math.round(o).toLocaleString():Math.round(o).toLocaleString()} (${l.toFixed(1)}%) below ${s} average`}return`Same as ${s} average`}catch{return""}}function m(e,t="households"){if(!e||e<=0)return"";const s=e/100,r=[[1,2,.5],[1,3,.333],[2,3,.666],[1,4,.25],[3,4,.75],[1,5,.2],[2,5,.4],[3,5,.6],[4,5,.8],[1,6,.166],[5,6,.833],[1,7,.142],[2,7,.285],[3,7,.428],[4,7,.571],[5,7,.714],[6,7,.857],[1,8,.125],[1,9,.111]],[n,c,o]=r.reduce((f,u)=>Math.abs(s-u[2])<Math.abs(s-f[2])?u:f),l=s-o;let d="";return Math.abs(l)>=.002&&(l>0?d=l<.01?"just over ":"over ":d=l>-.01?"just under ":"under "),`${d}${n} in ${c}${t?" "+t:""}`}function S(e){if(!e)return"Unknown";let t=e;if(t.includes(", Hawaii")){const s=t.replace(" County, Hawaii","").replace(", Hawaii","");t={Honolulu:"Honolulu County",Hawaii:"Hawaiʻi County",Maui:"Maui County",Kauai:"Kauaʻi County"}[s]||`${s} County`}else/House District|Senate District/.test(t)&&(t.includes(";")&&(t=t.split(";")[0].trim()),t=t.replace(/,?\s*Hawaii/,"").replace(/\s*\(\d{4}\)\s*/g,"").trim(),t.startsWith("House District")&&(t=t.replace("House District","State House District")),t.startsWith("Senate District")&&(t=t.replace("Senate District","State Senate District")));return t}function b(e,t){const s=(t==null?void 0:t.economic)||{},r=(t==null?void 0:t.housing)||{},n=e.median_income,c=e.median_rent,o=parseFloat(e.alice_rate)||0,l=e.snap_household_rate,d=e.snap_benefits_annual_total,f=e.snap_benefit_annual_per_household,u=f?parseFloat(f)/12:0,y=u?u/30:0,v=e.rent_burden_rate,g=e.severe_rent_burden_rate;let h=e.renter_rate;if(h!=null){const p=parseFloat(h);h=p>=0&&p<=1?+(p*100).toFixed(1):+p.toFixed(1)}return{name:S(e.display_name||e.NAME||e.name),population:i(e.total_population),medianIncome:i(n,{isCurrency:!0}),incomeVsState:_(n,s.median_income,"state",!0),medianRent:i(c,{isCurrency:!0}),rentVsState:_(c,r.median_rent,"state",!0),aliceRate:i(o,{isPercent:!0}),aliceFraction:m(o,"households")||"many households",snapRate:i(l,{isPercent:!0}),snapTotal:i(d,{isCurrency:!0}),avgMonthlyBenefit:i(u,{isCurrency:!0,decimals:2}),dailyPerPerson:i(y,{isCurrency:!0,decimals:2}),ctcAvg:i(e.ctc_avg_amount,{isCurrency:!0}),ctcRate:i(e.ctc_participation_rate,{isPercent:!0}),eitcAvg:i(e.federal_eitc_avg_amount,{isCurrency:!0}),eitcRate:i(e.eitc_participation_rate,{isPercent:!0}),stateEitcAvg:i(e.state_eitc_avg_amount,{isCurrency:!0}),travelTime:i(e.travel_time_to_work_minutes,{decimals:1}),transitPct:i(e.public_transportation_pct,{isPercent:!0}),renterRate:h!=null?h+"%":"N/A",rentBurden:i(v,{isPercent:!0}),rentBurdenFraction:m(parseFloat(v)||0,"renters")||"N/A",severeRentBurden:i(g,{isPercent:!0}),severeRentBurdenFraction:m(parseFloat(g)||0,"renters")||"N/A",cepDisplay:e.cep_display||"N/A",cepPct:i(e.cep_percentage,{isPercent:!0}),totalSchools:e.total_schools||"N/A",cepSchools:e.cep_schools||"N/A"}}function a(e){return String(e??"").replace(/[&<>"']/g,t=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[t])}function F(e){const t=`Fact Sheet: ${e.name}`,s=e.name.toUpperCase();return`
    <button class="print-button" onclick="window.print()">Save PDF</button>
    <div class="fact-sheet-container">
      <div class="fs-header">
        <img src="/hawaii-appleseed-dashboard/assets/logo.png" class="fs-logo" alt="Hawaii Appleseed" onerror="this.style.display='none'">
        <div class="fs-header-title">${a(t)}</div>
      </div>

      <div class="fs-main">
        <div class="fs-did-you-know">
          <h3>Did you know?</h3>
          <p>${a(e.aliceFraction)} (${a(e.aliceRate)}) are employed, yet struggling to make ends meet.</p>
        </div>

        <div class="fs-stats-row">
          <div class="fs-stat-card">
            <span class="fs-stat-number">${a(e.population)}</span>
            <div class="fs-stat-label">Total Population</div>
          </div>
          <div class="fs-stat-card">
            <span class="fs-stat-number">${a(e.medianIncome)}</span>
            <div class="fs-stat-label">Median Income</div>
            <div class="fs-stat-comparison">${a(e.incomeVsState)}</div>
          </div>
          <div class="fs-stat-card">
            <span class="fs-stat-number">${a(e.medianRent)}</span>
            <div class="fs-stat-label">Median Rent</div>
            <div class="fs-stat-comparison">${a(e.rentVsState)}</div>
          </div>
        </div>

        <div class="fs-grid">
          <div class="fs-card">
            <h3>Tax Credits</h3>
            <h4>Child Tax Credit (CTC)</h4>
            <ul>
              <li>Families receive an average of <span class="fs-hi">${a(e.ctcAvg)}</span> per year, with a participation rate of <span class="fs-hi">${a(e.ctcRate)}</span>.</li>
            </ul>
            <h4>Federal Earned Income Tax Credit (EITC)</h4>
            <ul>
              <li>Working families receive an average of <span class="fs-hi">${a(e.eitcAvg)}</span> annually, with <span class="fs-hi">${a(e.eitcRate)}</span> of eligible families participating.</li>
            </ul>
            <h4>State Earned Income Tax Credit</h4>
            <ul>
              <li>Hawaii's state EITC provides an additional <span class="fs-hi">${a(e.stateEitcAvg)}</span> on average to working families.</li>
            </ul>
          </div>

          <div class="fs-card">
            <h3>Food Security</h3>
            <h4>SNAP</h4>
            <ul>
              <li>About <strong>${a(e.snapRate)}</strong> of households participate in SNAP.</li>
              <li>Participants receive an average of <span class="fs-hi">${a(e.avgMonthlyBenefit)}</span> per month — about <span class="fs-hi">${a(e.dailyPerPerson)}</span> per person per day.</li>
              <li>SNAP brought <span class="fs-hi">${a(e.snapTotal)}</span> in benefits to ${a(s)}.</li>
            </ul>
            <h4>School Meals (CEP)</h4>
            <ul>
              <li><strong>${a(e.cepPct)}</strong> of schools (${a(e.cepSchools)} of ${a(e.totalSchools)}) provide free meals to all students through CEP.</li>
              ${e.cepDisplay&&e.cepDisplay!=="N/A"?`<li>${a(e.cepDisplay)}</li>`:""}
            </ul>
          </div>
        </div>

        <div class="fs-grid fs-grid-second">
          <div class="fs-card">
            <h3>Transportation</h3>
            <ul>
              <li>Average travel time to work: <strong>${a(e.travelTime)} minutes</strong>.</li>
              <li><strong>${a(e.transitPct)}</strong> of workers use public transportation.</li>
              <li>Longer commutes reduce quality of life and increase costs for low-income families.</li>
            </ul>
          </div>

          <div class="fs-card">
            <h3>Housing</h3>
            <ul>
              <li><strong>${a(e.renterRate)} of households</strong> are renters, with a median rent of <span class="fs-hi">${a(e.medianRent)}</span> per month.</li>
              <li><strong>${a(e.rentBurden)}</strong> of renters (${a(e.rentBurdenFraction)}) are cost-burdened, spending more than 30% of income on housing.</li>
              <li><strong>${a(e.severeRentBurden)}</strong> of renters (${a(e.severeRentBurdenFraction)}) are <em>severely</em> cost-burdened, spending more than 50%.</li>
            </ul>
          </div>
        </div>
      </div>

      <div class="fs-footer">
        <div class="fs-footer-brand">
          <img src="/hawaii-appleseed-dashboard/assets/logo.png" alt="" onerror="this.style.display='none'" style="height:30px">
          <span>HAWAIʻI APPLESEED<br><small>CENTER FOR LAW &amp; ECONOMIC JUSTICE</small></span>
        </div>
        <div class="fs-footer-url">www.hiappleseed.org/data-dashboard</div>
      </div>
    </div>`}async function w(){const e=new URLSearchParams(window.location.search),t=e.get("geo_id"),s=e.get("level")||"county",r=document.getElementById("factsheet-root");if(!t){r.innerHTML='<p class="fs-error">No geography selected. Open this page from the map by clicking a region.</p>';return}try{const[n,c]=await Promise.all([$(`/data/${s}.geojson`),$("/data/state_summary.json").catch(()=>({}))]),o=n.features.find(d=>String(d.properties.GEOID)===String(t)||String(d.properties.geoid)===String(t));if(!o){r.innerHTML=`<p class="fs-error">Geography not found: ${t}</p>`;return}const l=b(o.properties,c);document.title=`Fact Sheet: ${l.name}`,r.innerHTML=F(l)}catch(n){console.error("Fact sheet error:",n),r.innerHTML=`<p class="fs-error">Failed to load fact sheet: ${n.message}</p>`}}w();
