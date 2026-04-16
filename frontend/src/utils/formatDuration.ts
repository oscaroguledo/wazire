/**
 * Format duration in hours to a readable string
 * Treats decimal as hours.minutes (e.g., 2.5 = 2 hrs 50 min, 1.25 = 1 hr 25 min)
 */
export function formatDuration(hours: number): string {
  if (hours === 0) return '0 min';
  
  const hoursStr = hours.toString();
  const decimalIndex = hoursStr.indexOf('.');
  
  let wholeHours: number;
  let minutes: number;
  
  if (decimalIndex === -1) {
    // No decimal part
    wholeHours = hours;
    minutes = 0;
  } else {
    // Get whole hours and treat decimal part as literal minutes
    wholeHours = parseInt(hoursStr.substring(0, decimalIndex), 10);
    const decimalPart = hoursStr.substring(decimalIndex + 1);
    minutes = parseInt(decimalPart, 10);
  }
  
  if (wholeHours === 0) {
    return `${minutes} min`;
  }
  
  if (minutes === 0) {
    return wholeHours === 1 ? '1 hr' : `${wholeHours} hrs`;
  }
  
  const hrLabel = wholeHours === 1 ? 'hr' : 'hrs';
  return `${wholeHours} ${hrLabel} ${minutes} min`;
}
