# Architecture Improvement Proposal

## Current Issues

### 1. **Monolithic main.py (2092 lines)**
- **Problem**: All presentation logic, business logic, and UI components in one file
- **Impact**: Hard to maintain, test, and understand
- **Solution**: Split into focused modules

### 2. **Business Logic in Presentation Layer**
- **Problem**: `TimeClockApp` contains business logic (`perform_clock_action`, `handle_scan`)
- **Impact**: Violates separation of concerns, hard to test
- **Solution**: Extract to service layer

### 3. **Tight Coupling**
- **Problem**: Screens directly call database functions, app class knows about all screens
- **Impact**: Changes ripple through codebase, testing is difficult
- **Solution**: Introduce service layer and dependency injection

### 4. **No Clear State Management**
- **Problem**: Application state (`last_clocked_employee`, `_pending_identification`) scattered in app class
- **Impact**: State management is unclear, race conditions possible
- **Solution**: Dedicated state manager

### 5. **Inconsistent Error Handling**
- **Problem**: Mix of popups, logging, and silent failures
- **Impact**: Poor user experience, hard to debug
- **Solution**: Centralized error handling service

### 6. **Popup Management Scattered**
- **Problem**: Popup creation logic spread throughout codebase
- **Impact**: Inconsistent UX, hard to maintain
- **Solution**: Popup factory/service

---

## Proposed Architecture

```
src/
├── __init__.py
├── main.py                    # Minimal app entry point (~100 lines)
├── config.py                  # Configuration management
│
├── presentation/               # PRESENTATION LAYER
│   ├── __init__.py
│   ├── screens/               # Screen controllers
│   │   ├── __init__.py
│   │   ├── timeclock_screen.py
│   │   ├── admin_screen.py
│   │   ├── register_screen.py
│   │   ├── identify_screen.py
│   │   └── wt_report_screens.py
│   │
│   ├── popups/                # Popup components
│   │   ├── __init__.py
│   │   ├── greeter_popup.py
│   │   ├── badge_identification_popup.py
│   │   ├── entry_editor_popup.py
│   │   ├── date_picker_popup.py
│   │   ├── time_picker_popup.py
│   │   └── add_entry_popup.py
│   │
│   ├── widgets/               # Custom widgets
│   │   ├── __init__.py
│   │   ├── debounced_button.py
│   │   ├── filtered_text_input.py
│   │   └── input_filters.py
│   │
│   └── app.py                 # Main app class (orchestration only)
│
├── services/                  # BUSINESS LAYER
│   ├── __init__.py
│   ├── clock_service.py       # Clock in/out logic
│   ├── employee_service.py    # Employee management
│   ├── report_service.py      # Report generation
│   ├── export_service.py      # Export operations
│   ├── state_service.py       # Application state management
│   └── popup_service.py      # Popup management
│
├── data/                      # DATA LAYER (existing)
│   ├── database.py
│   └── models.py              # Extract models if needed
│
├── hardware/                  # HARDWARE LAYER (existing)
│   ├── rfid.py
│   └── screensaver.py
│
├── utils/                     # UTILITIES
│   ├── __init__.py
│   ├── export_utils.py
│   ├── wt_report.py
│   └── errors.py              # Error handling utilities
│
└── timeclock.kv              # UI definitions (existing)
```

---

## Detailed Improvements

### 1. Service Layer (`services/`)

#### `clock_service.py`
```python
class ClockService:
    """Handles clock in/out business logic"""
    
    def __init__(self, db_service, rfid_provider):
        self.db = db_service
        self.rfid = rfid_provider
    
    def clock_in_out(self, employee: Employee) -> ClockResult:
        """Perform clock action for employee"""
        last_entry = self.db.get_last_entry(employee)
        action = self._determine_action(last_entry)
        
        entry = self.db.create_time_entry(employee, action)
        
        return ClockResult(
            success=True,
            action=action,
            entry=entry,
            employee=employee
        )
    
    def _determine_action(self, last_entry) -> str:
        """Determine next action based on last entry"""
        if not last_entry or last_entry.action == 'out':
            return 'in'
        return 'out'
```

#### `state_service.py`
```python
class StateService:
    """Manages application state"""
    
    def __init__(self):
        self._last_clocked_employee: Optional[Employee] = None
        self._pending_identification: Optional[PendingId] = None
        self._recent_scans: Dict[str, float] = {}
    
    @property
    def last_clocked_employee(self) -> Optional[Employee]:
        return self._last_clocked_employee
    
    def set_last_clocked_employee(self, employee: Employee, timeout: int = 120):
        """Set last clocked employee with timeout"""
        self._last_clocked_employee = employee
        # Schedule timeout...
    
    def is_recent_scan(self, tag_id: str, threshold: float = 1.2) -> bool:
        """Check if scan is within debounce threshold"""
        # Implementation...
```

#### `popup_service.py`
```python
class PopupService:
    """Centralized popup management"""
    
    def show_info(self, title: str, message: str, duration: float = 3.0):
        """Show informational popup"""
        # Implementation...
    
    def show_error(self, title: str, message: str):
        """Show error popup"""
        # Implementation...
    
    def show_greeter(self, employee: Employee, action: str):
        """Show greeter popup"""
        # Implementation...
```

### 2. Refactored App Class (`presentation/app.py`)

```python
class TimeClockApp(App):
    """Main application - orchestration only"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize services
        self.state_service = StateService()
        self.clock_service = ClockService(self.db_service, self.rfid)
        self.popup_service = PopupService()
        # ... other services
    
    def build(self):
        """Build UI - minimal logic"""
        initialize_db()
        self.rfid = get_rfid_provider(self.on_rfid_scan)
        self.rfid.start()
        return self.root
    
    def on_rfid_scan(self, tag_id: str):
        """RFID callback - delegate to service"""
        Clock.schedule_once(
            lambda dt: self.clock_service.handle_scan(tag_id, self.root.current),
            0
        )
```

### 3. Screen Controllers (`presentation/screens/`)

```python
# presentation/screens/timeclock_screen.py
class TimeClockScreen(Screen):
    """TimeClock screen controller"""
    
    def __init__(self, clock_service, popup_service, **kwargs):
        super().__init__(**kwargs)
        self.clock_service = clock_service
        self.popup_service = popup_service
    
    def on_clock_action(self, employee: Employee):
        """Handle clock action request"""
        result = self.clock_service.clock_in_out(employee)
        if result.success:
            self.popup_service.show_greeter(result.employee, result.action)
            self.update_status(f"Clocked {result.action.upper()}")
```

### 4. Error Handling (`utils/errors.py`)

```python
class TimeClockError(Exception):
    """Base exception for TimeClock"""
    pass

class EmployeeNotFoundError(TimeClockError):
    """Employee not found"""
    pass

class InvalidActionError(TimeClockError):
    """Invalid clock action"""
    pass

class ErrorHandler:
    """Centralized error handling"""
    
    @staticmethod
    def handle_error(error: Exception, popup_service: PopupService):
        """Handle and display errors"""
        if isinstance(error, EmployeeNotFoundError):
            popup_service.show_error("Error", "Employee not found")
        elif isinstance(error, InvalidActionError):
            popup_service.show_error("Error", "Invalid action")
        else:
            logger.exception("Unexpected error")
            popup_service.show_error("Error", "An unexpected error occurred")
```

---

## Migration Strategy

### Phase 1: Extract Services (Low Risk)
1. Create `services/` directory
2. Extract `ClockService` from `TimeClockApp.perform_clock_action`
3. Extract `StateService` from app state variables
4. Update app to use services (keep existing code working)

### Phase 2: Split main.py (Medium Risk)
1. Create `presentation/` directory structure
2. Move popups to `presentation/popups/`
3. Move screens to `presentation/screens/`
4. Move widgets to `presentation/widgets/`
5. Update imports

### Phase 3: Refactor App Class (Low Risk)
1. Move business logic to services
2. Make app class orchestration-only
3. Add dependency injection

### Phase 4: Improve Error Handling (Low Risk)
1. Create error classes
2. Add error handler service
3. Update all error handling to use centralized approach

---

## Benefits

### 1. **Maintainability**
- Smaller, focused files
- Clear separation of concerns
- Easier to locate code

### 2. **Testability**
- Services can be unit tested independently
- Mock dependencies easily
- Test business logic without UI

### 3. **Scalability**
- Easy to add new features
- Services can be reused
- Clear extension points

### 4. **Code Quality**
- Reduced coupling
- Better error handling
- Consistent patterns

### 5. **Developer Experience**
- Easier onboarding
- Clear architecture
- Better IDE support

---

## Example: Refactored Clock Flow

### Before (Current)
```python
# In TimeClockApp
def perform_clock_action(self, employee):
    last_entry = TimeEntry.get_last_for_employee(employee)
    action = 'in' if not last_entry or last_entry.action == 'out' else 'out'
    create_time_entry(employee, action)
    self.show_greeter(employee, action)
    # ... UI updates ...
```

### After (Improved)
```python
# In ClockService
def clock_in_out(self, employee: Employee) -> ClockResult:
    last_entry = self.db.get_last_entry(employee)
    action = self._determine_action(last_entry)
    entry = self.db.create_time_entry(employee, action)
    return ClockResult(success=True, action=action, entry=entry, employee=employee)

# In TimeClockScreen
def on_clock_action(self, employee: Employee):
    result = self.clock_service.clock_in_out(employee)
    if result.success:
        self.popup_service.show_greeter(result.employee, result.action)
        self.update_status(f"Clocked {result.action.upper()}")
```

---

## Additional Improvements

### 1. **Configuration Management**
- Move all config to `config.py`
- Environment-based configuration
- Validation on startup

### 2. **Event System**
- Publish/subscribe for loose coupling
- Events: `clock_in`, `clock_out`, `employee_registered`
- Services can react to events

### 3. **Logging Improvements**
- Structured logging
- Log levels per component
- Log rotation

### 4. **Type Hints**
- Add type hints throughout
- Better IDE support
- Catch errors early

### 5. **Documentation**
- Docstrings for all public APIs
- Architecture diagrams
- API documentation

---

## Priority Recommendations

### High Priority (Do First)
1. ✅ Extract `ClockService` - Core business logic
2. ✅ Extract `StateService` - State management
3. ✅ Create `PopupService` - Consistent UX

### Medium Priority (Do Next)
4. Split `main.py` into modules
5. Extract screen controllers
6. Improve error handling

### Low Priority (Nice to Have)
7. Add event system
8. Configuration management
9. Type hints throughout

---

## Conclusion

The proposed architecture maintains backward compatibility while significantly improving:
- **Code organization**: Clear module structure
- **Separation of concerns**: Business logic separated from presentation
- **Testability**: Services can be tested independently
- **Maintainability**: Smaller, focused files
- **Scalability**: Easy to extend

The migration can be done incrementally, reducing risk and allowing the application to remain functional throughout the refactoring process.

