import { useState } from 'react';
import { Calendar, Clock, ChevronDown, ChevronLeft, ChevronRight } from 'lucide-react';
import Icon from '@/components/Icon';

interface DateTimePickerProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function DateTimePicker({ value, onChange, disabled = false, placeholder = "Select date and time" }: DateTimePickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [activeTab, setActiveTab] = useState<'date' | 'time'>('date');

  // Parse current value - handle both UTC ISO and local formats
  const parseValue = (val: string) => {
    if (!val) return { date: '', time: '' };
    // Parse the full ISO string with timezone
    const d = new Date(val);
    if (isNaN(d.getTime())) {
      // Fallback to old parsing for backward compatibility
      const [date, time] = val.split('T');
      return { date: date || '', time: time ? time.substring(0, 5) : '' };
    }
    // Get local date/time for display
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    return { 
      date: `${year}-${month}-${day}`, 
      time: `${hours}:${minutes}` 
    };
  };

  const { date, time } = parseValue(value);
  const selectedDate = date ? new Date(date) : null;

  const handleDateSelect = (year: number, month: number, day: number) => {
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    const timeStr = time || '00:00';
    // Build local datetime and send with timezone offset
    const localDateStr = `${dateStr}T${timeStr}`;
    const localDate = new Date(localDateStr);
    // Get timezone offset in minutes and create ISO string with local timezone
    const offset = -localDate.getTimezoneOffset();
    const offsetSign = offset >= 0 ? '+' : '-';
    const offsetHours = Math.abs(Math.floor(offset / 60)).toString().padStart(2, '0');
    const offsetMinutes = Math.abs(offset % 60).toString().padStart(2, '0');
    const localIsoString = `${localDateStr}:00${offsetSign}${offsetHours}:${offsetMinutes}`;
    onChange(localIsoString);
    setActiveTab('time');
  };

  const handleTimeSelect = (hour: number, minute: number) => {
    const timeStr = `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
    if (!date) return;
    // Build local datetime and send with timezone offset
    const localDateStr = `${date}T${timeStr}`;
    const localDate = new Date(localDateStr);
    // Get timezone offset in minutes and create ISO string with local timezone
    const offset = -localDate.getTimezoneOffset();
    const offsetSign = offset >= 0 ? '+' : '-';
    const offsetHours = Math.abs(Math.floor(offset / 60)).toString().padStart(2, '0');
    const offsetMinutes = Math.abs(offset % 60).toString().padStart(2, '0');
    const localIsoString = `${localDateStr}:00${offsetSign}${offsetHours}:${offsetMinutes}`;
    onChange(localIsoString);
  };

  const formatDisplay = () => {
    if (!value) return placeholder;
    const d = new Date(value);
    if (isNaN(d.getTime())) return placeholder;
    return d.toLocaleString('en-US', {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Calendar logic
  const getDaysInMonth = (year: number, month: number) => {
    return new Date(year, month + 1, 0).getDate();
  };

  const getFirstDayOfMonth = (year: number, month: number) => {
    return new Date(year, month, 1).getDay();
  };

  const year = currentMonth.getFullYear();
  const month = currentMonth.getMonth();
  const daysInMonth = getDaysInMonth(year, month);
  const firstDay = getFirstDayOfMonth(year, month);

  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  const weekDays = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];

  // Generate time slots
  const timeSlots = [];
  for (let h = 0; h < 24; h++) {
    for (let m = 0; m < 60; m += 30) {
      timeSlots.push({ hour: h, minute: m });
    }
  }

  const prevMonth = () => {
    setCurrentMonth(new Date(year, month - 1, 1));
  };

  const nextMonth = () => {
    setCurrentMonth(new Date(year, month + 1, 1));
  };

  const isSelectedDate = (day: number) => {
    if (!selectedDate) return false;
    return selectedDate.getDate() === day && 
           selectedDate.getMonth() === month && 
           selectedDate.getFullYear() === year;
  };

  const isToday = (day: number) => {
    const today = new Date();
    return today.getDate() === day && 
           today.getMonth() === month && 
           today.getFullYear() === year;
  };

  return (
    <div className="relative">
      {/* Display Button */}
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className={`w-full flex items-center gap-3 px-3 py-2 border rounded-lg transition-all duration-200 ${
          disabled 
            ? 'bg-[var(--color-bg-hover)] border-[var(--color-border-light)] cursor-not-allowed' 
            : 'bg-[var(--color-bg-card)] border-[var(--color-border-light)] hover:border-[var(--color-primary-400)] focus:border-[var(--color-primary-500)] focus:ring-2 focus:ring-[var(--color-primary-100)]'
        }`}
      >
        <div className="flex items-center gap-2 text-[var(--color-text-muted)]">
          <Icon as={Calendar} size={18} />
          <span className="text-[var(--color-text-muted)]">|</span>
          <Icon as={Clock} size={16} />
        </div>
        <span className={`flex-1 text-left ${value ? 'text-[var(--color-text-primary)]' : 'text-[var(--color-text-muted)]'}`}>
          {formatDisplay()}
        </span>
        <Icon as={ChevronDown} size={16} className="text-[var(--color-text-muted)]" />
      </button>

      {/* Dropdown */}
      {isOpen && !disabled && (
        <div 
          className="absolute top-full left-0 right-0 mt-1 bg-[var(--color-bg-card)] border border-[var(--color-border-light)] rounded-lg shadow-lg z-50 p-4"
          onClick={(e) => e.stopPropagation()}
          onMouseDown={(e) => e.stopPropagation()}
        >
          {/* Tabs */}
          <div className="flex gap-2 mb-4">
            <button
              type="button"
              onClick={() => setActiveTab('date')}
              className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'date'
                  ? 'bg-[var(--color-primary-50)] text-[var(--color-primary-700)]'
                  : 'bg-[var(--color-bg-hover)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]'
              }`}
            >
              <span className="flex items-center justify-center gap-2">
                <Icon as={Calendar} size={14} />
                Date
              </span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('time')}
              className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'time'
                  ? 'bg-[var(--color-primary-50)] text-[var(--color-primary-700)]'
                  : 'bg-[var(--color-bg-hover)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]'
              }`}
            >
              <span className="flex items-center justify-center gap-2">
                <Icon as={Clock} size={14} />
                Time
              </span>
            </button>
          </div>

          {/* Calendar Widget */}
          {activeTab === 'date' && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <button
                  type="button"
                  onClick={prevMonth}
                  className="p-1 hover:bg-[var(--color-bg-hover)] rounded-md transition-colors"
                >
                  <Icon as={ChevronLeft} size={20} className="text-[var(--color-text-secondary)]" />
                </button>
                <span className="font-medium text-[var(--color-text-primary)]">
                  {monthNames[month]} {year}
                </span>
                <button
                  type="button"
                  onClick={nextMonth}
                  className="p-1 hover:bg-[var(--color-bg-hover)] rounded-md transition-colors"
                >
                  <Icon as={ChevronRight} size={20} className="text-[var(--color-text-secondary)]" />
                </button>
              </div>

              {/* Week day headers */}
              <div className="grid grid-cols-7 gap-1 mb-2">
                {weekDays.map((day) => (
                  <div key={day} className="text-center text-xs font-medium text-[var(--color-text-muted)] py-1">
                    {day}
                  </div>
                ))}
              </div>

              {/* Calendar days */}
              <div className="grid grid-cols-7 gap-1">
                {Array.from({ length: firstDay }).map((_, i) => (
                  <div key={`empty-${i}`} className="h-8" />
                ))}
                {Array.from({ length: daysInMonth }).map((_, i) => {
                  const day = i + 1;
                  const selected = isSelectedDate(day);
                  const today = isToday(day);
                  return (
                    <button
                      key={day}
                      type="button"
                      onClick={() => handleDateSelect(year, month, day)}
                      className={`h-8 w-8 rounded-md text-sm font-medium transition-colors ${
                        selected
                          ? 'bg-[var(--color-primary-600)] text-white'
                          : today
                          ? 'bg-[var(--color-primary-50)] text-[var(--color-primary-700)]'
                          : 'hover:bg-[var(--color-bg-hover)] text-[var(--color-text-secondary)]'
                      }`}
                    >
                      {day}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Clock Widget */}
          {activeTab === 'time' && (
            <div>
              <div className="grid grid-cols-4 gap-2 max-h-48 overflow-y-auto">
                {timeSlots.map(({ hour, minute }) => {
                  const timeStr = `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
                  const isSelected = time === timeStr;
                  return (
                    <button
                      key={timeStr}
                      type="button"
                      onClick={() => handleTimeSelect(hour, minute)}
                      className={`px-2 py-1.5 rounded-md text-sm font-medium transition-colors ${
                        isSelected
                          ? 'bg-[var(--color-primary-600)] text-white'
                          : 'bg-[var(--color-bg-hover)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]'
                      }`}
                    >
                      {timeStr}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Quick Actions */}
          <div className="flex gap-2 mt-4 pt-3 border-t border-[var(--color-border-light)]">
            <button
              type="button"
              onClick={() => {
                // Emit local datetime with timezone offset
                const now = new Date();
                const offset = -now.getTimezoneOffset();
                const offsetSign = offset >= 0 ? '+' : '-';
                const offsetHours = Math.abs(Math.floor(offset / 60)).toString().padStart(2, '0');
                const offsetMinutes = Math.abs(offset % 60).toString().padStart(2, '0');
                const year = now.getFullYear();
                const month = String(now.getMonth() + 1).padStart(2, '0');
                const day = String(now.getDate()).padStart(2, '0');
                const hours = String(now.getHours()).padStart(2, '0');
                const minutes = String(now.getMinutes()).padStart(2, '0');
                const localIsoString = `${year}-${month}-${day}T${hours}:${minutes}:00${offsetSign}${offsetHours}:${offsetMinutes}`;
                onChange(localIsoString);
                setIsOpen(false);
              }}
              className="flex-1 px-3 py-1.5 text-xs bg-[var(--color-primary-50)] text-[var(--color-primary-700)] rounded-md hover:bg-[var(--color-primary-50)] transition-colors"
            >
              Now
            </button>
            <button
              type="button"
              onClick={() => {
                // Build local tomorrow 9:00 and emit with timezone offset
                const tomorrow = new Date();
                tomorrow.setDate(tomorrow.getDate() + 1);
                tomorrow.setHours(9, 0, 0, 0);
                const offset = -tomorrow.getTimezoneOffset();
                const offsetSign = offset >= 0 ? '+' : '-';
                const offsetHours = Math.abs(Math.floor(offset / 60)).toString().padStart(2, '0');
                const offsetMinutes = Math.abs(offset % 60).toString().padStart(2, '0');
                const year = tomorrow.getFullYear();
                const month = String(tomorrow.getMonth() + 1).padStart(2, '0');
                const day = String(tomorrow.getDate()).padStart(2, '0');
                const localIsoString = `${year}-${month}-${day}T09:00:00${offsetSign}${offsetHours}:${offsetMinutes}`;
                onChange(localIsoString);
                setIsOpen(false);
              }}
              className="flex-1 px-3 py-1.5 text-xs bg-[var(--color-bg-hover)] text-[var(--color-text-secondary)] rounded-md hover:bg-[var(--color-bg-hover)] transition-colors"
            >
              Tomorrow 9AM
            </button>
          </div>

          {/* Close Button */}
          <div className="mt-3">
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="w-full px-3 py-2 text-sm bg-[var(--color-bg-hover)] text-[var(--color-text-secondary)] rounded-lg hover:bg-[var(--color-bg-subtle)] transition-colors"
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default DateTimePicker;
