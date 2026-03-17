from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from collections import deque
from typing import Deque, Dict, Optional, Literal


CustomerType = Literal["regular", "priority"]


@dataclass(frozen=True, slots=True)
class Ticket:
    number: int
    customer_type: CustomerType
    issued_at_iso: str  # ISO string for display/logging


class QueueManager:
    """
    In-memory queue system:
    - Two queues (regular, priority) implemented as deques (queue DS).
    - A dict (hash table DS) for O(1) ticket lookup by ticket number.
    """

    def __init__(self, *, ticket_start: int = 0, service_minutes_per_customer: int = 6):
        self._ticket_counter: int = ticket_start
        self._regular: Deque[int] = deque()
        self._priority: Deque[int] = deque()
        self._tickets: Dict[int, Ticket] = {}
        self._current: Optional[int] = None
        self._service_minutes: int = service_minutes_per_customer
        self._day: date = date.today()

    @property
    def service_minutes_per_customer(self) -> int:
        return self._service_minutes

    @property
    def today(self) -> date:
        return self._day

    def ensure_today(self, today: Optional[date] = None) -> None:
        """Reset automatically if day changes."""
        today = today or date.today()
        if today != self._day:
            self.reset(today=today)

    def reset(self, *, today: Optional[date] = None) -> None:
        """O(1) reset (clears references)."""
        self._ticket_counter = 0
        self._regular.clear()
        self._priority.clear()
        self._tickets.clear()
        self._current = None
        self._day = today or date.today()

    def issue_ticket(self, *, customer_type: CustomerType, issued_at_iso: str) -> Ticket:
        """
        O(1):
        - increment counter
        - append to one deque
        - store in dict
        """
        self._ticket_counter += 1
        t = Ticket(number=self._ticket_counter, customer_type=customer_type, issued_at_iso=issued_at_iso)
        self._tickets[t.number] = t
        if customer_type == "priority":
            self._priority.append(t.number)
        else:
            self._regular.append(t.number)
        return t

    def call_next(self) -> Optional[Ticket]:
        """
        O(1): pop from priority if available, else from regular.
        """
        if self._priority:
            self._current = self._priority.popleft()
        elif self._regular:
            self._current = self._regular.popleft()
        else:
            self._current = None
            return None
        return self._tickets.get(self._current)

    def current_ticket(self) -> Optional[Ticket]:
        if self._current is None:
            return None
        return self._tickets.get(self._current)

    def waiting_counts(self) -> dict:
        """O(1) sizes."""
        return {
            "priority": len(self._priority),
            "regular": len(self._regular),
            "total": len(self._priority) + len(self._regular),
        }

    def waiting_ticket_numbers(self) -> dict:
        """
        O(n) to materialize lists for display purposes.
        Returns ticket numbers in their queue order.
        """
        return {
            "priority": list(self._priority),
            "regular": list(self._regular),
        }

    def peek_next_ticket(self) -> Optional[Ticket]:
        """O(1): see who would be served next (without removing)."""
        if self._priority:
            return self._tickets.get(self._priority[0])
        if self._regular:
            return self._tickets.get(self._regular[0])
        return None

    def peek_after_next_ticket(self) -> Optional[Ticket]:
        """O(1): see who would be served after next (without removing)."""
        if len(self._priority) >= 2:
            return self._tickets.get(self._priority[1])
        if len(self._priority) == 1:
            # After the last priority, the first regular (if any) is next.
            if self._regular:
                return self._tickets.get(self._regular[0])
            return None
        # No priority at all: second regular (if any)
        if len(self._regular) >= 2:
            return self._tickets.get(self._regular[1])
        return None

    def estimate_wait_minutes_for_new_arrival(self, customer_type: CustomerType) -> int:
        """
        O(1) estimate based on counts only.
        Assumes fixed service time per customer.
        """
        if customer_type == "priority":
            ahead = len(self._priority)
        else:
            ahead = len(self._priority) + len(self._regular)
        return ahead * self._service_minutes

    def position_and_eta(self, ticket_number: int) -> Optional[dict]:
        """
        O(n): find the ticket's position by scanning deques.
        Returns None if ticket not waiting (already served or never existed).
        """
        t = self._tickets.get(ticket_number)
        if t is None:
            return None

        if t.customer_type == "priority":
            try:
                idx = list(self._priority).index(ticket_number)  # O(n)
            except ValueError:
                return None
            ahead = idx
        else:
            # Regular ticket: all priority are ahead, then those earlier in regular
            try:
                idx = list(self._regular).index(ticket_number)  # O(n)
            except ValueError:
                return None
            ahead = len(self._priority) + idx

        return {
            "ahead": ahead,
            "eta_minutes": ahead * self._service_minutes,
            "customer_type": t.customer_type,
        }

    def snapshot(self) -> dict:
        """Serialize minimal state for optional persistence."""
        return {
            "day": self._day.isoformat(),
            "ticket_counter": self._ticket_counter,
            "regular": list(self._regular),
            "priority": list(self._priority),
            "tickets": {str(k): asdict(v) for k, v in self._tickets.items()},
            "current": self._current,
            "service_minutes": self._service_minutes,
        }

    @staticmethod
    def from_snapshot(data: dict) -> "QueueManager":
        qm = QueueManager(
            ticket_start=int(data.get("ticket_counter", 0)),
            service_minutes_per_customer=int(data.get("service_minutes", 6)),
        )
        qm._day = date.fromisoformat(data.get("day", date.today().isoformat()))
        qm._regular = deque(int(x) for x in data.get("regular", []))
        qm._priority = deque(int(x) for x in data.get("priority", []))
        qm._current = data.get("current", None)
        qm._tickets = {}
        for k, v in (data.get("tickets", {}) or {}).items():
            num = int(k)
            # Accept both dict-like ticket payloads and older formats.
            if not isinstance(v, dict):
                continue
            qm._tickets[num] = Ticket(
                number=int(v["number"]),
                customer_type=v["customer_type"],
                issued_at_iso=v["issued_at_iso"],
            )
        return qm

