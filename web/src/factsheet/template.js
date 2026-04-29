function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));
}

export function generateFactSheetHTML(geo) {
  const title = `Fact Sheet: ${geo.name}`;
  const nameUpper = geo.name.toUpperCase();

  return `
    <button class="print-button" onclick="window.print()">Save PDF</button>
    <div class="fact-sheet-container">
      <div class="fs-header">
        <img src="/assets/logo.png" class="fs-logo" alt="Hawaii Appleseed" onerror="this.style.display='none'">
        <div class="fs-header-title">${esc(title)}</div>
      </div>

      <div class="fs-main">
        <div class="fs-did-you-know">
          <h3>Did you know?</h3>
          <p>${esc(geo.aliceFraction)} (${esc(geo.aliceRate)}) are employed, yet struggling to make ends meet.</p>
        </div>

        <div class="fs-stats-row">
          <div class="fs-stat-card">
            <span class="fs-stat-number">${esc(geo.population)}</span>
            <div class="fs-stat-label">Total Population</div>
          </div>
          <div class="fs-stat-card">
            <span class="fs-stat-number">${esc(geo.medianIncome)}</span>
            <div class="fs-stat-label">Median Income</div>
            <div class="fs-stat-comparison">${esc(geo.incomeVsState)}</div>
          </div>
          <div class="fs-stat-card">
            <span class="fs-stat-number">${esc(geo.medianRent)}</span>
            <div class="fs-stat-label">Median Rent</div>
            <div class="fs-stat-comparison">${esc(geo.rentVsState)}</div>
          </div>
        </div>

        <div class="fs-grid">
          <div class="fs-card">
            <h3>Tax Credits</h3>
            <h4>Child Tax Credit (CTC)</h4>
            <ul>
              <li>Families receive an average of <span class="fs-hi">${esc(geo.ctcAvg)}</span> per year, with a participation rate of <span class="fs-hi">${esc(geo.ctcRate)}</span>.</li>
            </ul>
            <h4>Federal Earned Income Tax Credit (EITC)</h4>
            <ul>
              <li>Working families receive an average of <span class="fs-hi">${esc(geo.eitcAvg)}</span> annually, with <span class="fs-hi">${esc(geo.eitcRate)}</span> of eligible families participating.</li>
            </ul>
            <h4>State Earned Income Tax Credit</h4>
            <ul>
              <li>Hawaii's state EITC provides an additional <span class="fs-hi">${esc(geo.stateEitcAvg)}</span> on average to working families.</li>
            </ul>
          </div>

          <div class="fs-card">
            <h3>Food Security</h3>
            <h4>SNAP</h4>
            <ul>
              <li>About <strong>${esc(geo.snapRate)}</strong> of households participate in SNAP.</li>
              <li>Participants receive an average of <span class="fs-hi">${esc(geo.avgMonthlyBenefit)}</span> per month — about <span class="fs-hi">${esc(geo.dailyPerPerson)}</span> per person per day.</li>
              <li>SNAP brought <span class="fs-hi">${esc(geo.snapTotal)}</span> in benefits to ${esc(nameUpper)}.</li>
            </ul>
            <h4>School Meals (CEP)</h4>
            <ul>
              <li><strong>${esc(geo.cepPct)}</strong> of schools (${esc(geo.cepSchools)} of ${esc(geo.totalSchools)}) provide free meals to all students through CEP.</li>
              ${geo.cepDisplay && geo.cepDisplay !== 'N/A' ? `<li>${esc(geo.cepDisplay)}</li>` : ''}
            </ul>
          </div>
        </div>

        <div class="fs-grid fs-grid-second">
          <div class="fs-card">
            <h3>Transportation</h3>
            <ul>
              <li>Average travel time to work: <strong>${esc(geo.travelTime)} minutes</strong>.</li>
              <li><strong>${esc(geo.transitPct)}</strong> of workers use public transportation.</li>
              <li>Longer commutes reduce quality of life and increase costs for low-income families.</li>
            </ul>
          </div>

          <div class="fs-card">
            <h3>Housing</h3>
            <ul>
              <li><strong>${esc(geo.renterRate)} of households</strong> are renters, with a median rent of <span class="fs-hi">${esc(geo.medianRent)}</span> per month.</li>
              <li><strong>${esc(geo.rentBurden)}</strong> of renters (${esc(geo.rentBurdenFraction)}) are cost-burdened, spending more than 30% of income on housing.</li>
              <li><strong>${esc(geo.severeRentBurden)}</strong> of renters (${esc(geo.severeRentBurdenFraction)}) are <em>severely</em> cost-burdened, spending more than 50%.</li>
            </ul>
          </div>
        </div>
      </div>

      <div class="fs-footer">
        <div class="fs-footer-brand">
          <img src="/assets/logo.png" alt="" onerror="this.style.display='none'" style="height:30px">
          <span>HAWAIʻI APPLESEED<br><small>CENTER FOR LAW &amp; ECONOMIC JUSTICE</small></span>
        </div>
        <div class="fs-footer-url">www.hiappleseed.org/data-dashboard</div>
      </div>
    </div>`;
}
