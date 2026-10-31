/**
 * Brightloop Software — Admin Dashboard Chart.js Visualizations
 */

document.addEventListener('DOMContentLoaded', function () {
  // 1. Revenue Trends Chart (Monthly Line/Area)
  const revCanvas = document.getElementById('revenueTrendsChart');
  if (revCanvas) {
    try {
      const revData = JSON.parse(revCanvas.dataset.chartData || '{}');
      const ctx = revCanvas.getContext('2d');
      
      const gradient = ctx.createLinearGradient(0, 0, 0, 320);
      gradient.addColorStop(0, 'rgba(99, 102, 241, 0.45)');
      gradient.addColorStop(1, 'rgba(99, 102, 241, 0.01)');

      new Chart(ctx, {
        type: 'line',
        data: {
          labels: revData.labels || [],
          datasets: [{
            label: 'Monthly Recurring Revenue ($)',
            data: revData.data || [],
            borderColor: '#6366f1',
            backgroundColor: gradient,
            borderWidth: 3,
            fill: true,
            tension: 0.35,
            pointBackgroundColor: '#ffffff',
            pointBorderColor: '#6366f1',
            pointBorderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: function (context) {
                  return ' ' + context.dataset.label + ': $' + Number(context.raw).toLocaleString();
                }
              }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              grid: { color: '#f1f5f9' },
              ticks: {
                callback: function (val) {
                  return '$' + Number(val).toLocaleString();
                }
              }
            },
            x: {
              grid: { display: false }
            }
          }
        }
      });
    } catch (e) {
      console.error('Failed to initialize Revenue Chart', e);
    }
  }

  // 2. Subscription Status Doughnut Chart
  const statusCanvas = document.getElementById('subscriptionStatusChart');
  if (statusCanvas) {
    try {
      const statusData = JSON.parse(statusCanvas.dataset.chartData || '{}');
      new Chart(statusCanvas, {
        type: 'doughnut',
        data: {
          labels: statusData.labels || ['Active', 'Trialing', 'Past Due', 'Canceled'],
          datasets: [{
            data: statusData.data || [0, 0, 0, 0],
            backgroundColor: [
              '#10b981', // emerald
              '#06b6d4', // cyan
              '#f59e0b', // amber
              '#94a3b8'  // slate
            ],
            borderWidth: 2,
            borderColor: '#ffffff',
            hoverOffset: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '72%',
          plugins: {
            legend: {
              position: 'bottom',
              labels: {
                usePointStyle: true,
                padding: 16,
                font: { size: 12, weight: '600' }
              }
            }
          }
        }
      });
    } catch (e) {
      console.error('Failed to initialize Status Chart', e);
    }
  }

  // 3. Subscription Plan Popularity (Bar Chart)
  const plansCanvas = document.getElementById('planPopularityChart');
  if (plansCanvas) {
    try {
      const plansData = JSON.parse(plansCanvas.dataset.chartData || '{}');
      new Chart(plansCanvas, {
        type: 'bar',
        data: {
          labels: plansData.labels || [],
          datasets: [{
            label: 'Active Subscribers',
            data: plansData.data || [],
            backgroundColor: '#8b5cf6',
            borderRadius: 6,
            borderSkipped: false
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: { precision: 0 },
              grid: { color: '#f1f5f9' }
            },
            x: {
              grid: { display: false }
            }
          }
        }
      });
    } catch (e) {
      console.error('Failed to initialize Plan Popularity Chart', e);
    }
  }
});
