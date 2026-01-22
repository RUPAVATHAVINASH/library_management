"""
Library Management & Fine Calculation System
-------------------------------------------
Features:
- Book Inventory  : Add, search, update, view books (with categories).
- Member Management: Register members, track borrowed books.
- Book Issue      : Validate availability, assign due dates.
- Return & Fines  : Auto-calc per-day late fines.
- Search Engine   : Keyword-based (title/author, member ID).
- Usage Tracking  : Issue history.
- Premium Add-ons : Block members above fine limit, categorized shelves,
                    auto-reminders for due/overdue books,
                    PDF export of borrowing & fines summary.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# ----------------- CONFIGURATION CONSTANTS -----------------
FINE_PER_DAY = 5          # Fine per late day (₹)
MAX_FINE_LIMIT = 500      # Block member if outstanding fine >= this
ISSUE_DAYS = 14           # Default issue period in days

DATE_FORMAT = "%d-%m-%Y"  # For displaying dates


# ----------------- DATA MODELS ----------------
@dataclass
class Book:
    book_id: str
    title: str
    author: str
    category: str          # Fiction / Science / etc.
    total_copies: int
    available_copies: int

    def __str__(self) -> str:
        return (
            f"[{self.book_id}] {self.title} by {self.author} | "
            f"Category: {self.category} | "
            f"Available: {self.available_copies}/{self.total_copies}"
        )


@dataclass
class Member:
    member_id: str
    name: str
    phone: str
    blocked: bool = False
    outstanding_fine: int = 0
    borrowed_books: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        status = "BLOCKED" if self.blocked else "ACTIVE"
        return (
            f"[{self.member_id}] {self.name} ({self.phone}) | "
            f"Books borrowed: {len(self.borrowed_books)} | "
            f"Outstanding fine: ₹{self.outstanding_fine} | Status: {status}"
        )


@dataclass
class IssueRecord:
    issue_id: int
    book_id: str
    member_id: str
    issue_date: datetime
    due_date: datetime
    return_date: Optional[datetime] = None
    fine_charged: int = 0

    def is_overdue(self, on_date: Optional[datetime] = None) -> bool:
        """Check if this issue is overdue on the given date (or today)."""
        if on_date is None:
            on_date = datetime.today()
        if self.return_date is not None:
            return self.return_date > self.due_date
        return on_date > self.due_date

    def days_late(self, on_date: Optional[datetime] = None) -> int:
        """Number of late days (0 if not late)."""
        if on_date is None:
            on_date = datetime.today()
        effective_date = self.return_date or on_date
        delta_days = (effective_date.date() - self.due_date.date()).days
        return max(0, delta_days)

    def __str__(self) -> str:
        status = "Returned" if self.return_date else "Issued"
        issue_str = self.issue_date.strftime(DATE_FORMAT)
        due_str = self.due_date.strftime(DATE_FORMAT)
        ret_str = self.return_date.strftime(DATE_FORMAT) if self.return_date else "-"
        return (
            f"IssueID: {self.issue_id} | Book: {self.book_id} | "
            f"Member: {self.member_id} | Issue: {issue_str} | Due: {due_str} | "
            f"Return: {ret_str} | Fine: ₹{self.fine_charged} | Status: {status}"
        )


# ----------------- IN-MEMORY "DATABASES" -----------------
books: Dict[str, Book] = {}
members: Dict[str, Member] = {}
issues: Dict[int, IssueRecord] = {}
next_issue_id: int = 1  # auto-increment issue IDs


# ----------------- HELPER FUNCTIONS -----------------
def input_int(prompt: str, minimum: int = 0) -> int:
    while True:
        try:
            value = int(input(prompt))
            if value < minimum:
                print(f"Value must be >= {minimum}")
                continue
            return value
        except ValueError:
            print("Please enter a valid integer.")


def pause() -> None:
    input("\nPress ENTER to continue...")


def check_and_update_block_status(member: Member) -> None:
    """Block member if outstanding fine crosses limit."""
    if member.outstanding_fine >= MAX_FINE_LIMIT:
        member.blocked = True
    else:
        member.blocked = False


# ----------------- BOOK FUNCTIONS ----------------
def add_book() -> None:
    print("\n--- Add New Book ---")
    book_id = input("Enter Book ID: ").strip()
    if book_id in books:
        print("Book ID already exists. Use update option instead.")
        return
    title = input("Enter Title: ").strip()
    author = input("Enter Author: ").strip()
    category = input("Enter Category (Fiction/Science/etc.): ").strip()
    total_copies = input_int("Enter Total Copies: ", minimum=1)

    books[book_id] = Book(
        book_id=book_id,
        title=title,
        author=author,
        category=category,
        total_copies=total_copies,
        available_copies=total_copies,
    )
    print("Book added successfully.")


def view_all_books() -> None:
    print("\n--- All Books ---")
    if not books:
        print("No books in inventory.")
        return
    for book in books.values():
        print(book)


def search_books() -> None:
    print("\n--- Search Books ---")
    keyword = input("Enter keyword (title/author/category): ").strip().lower()
    if not keyword:
        print("Keyword cannot be empty.")
        return

    results = [
        b for b in books.values()
        if keyword in b.title.lower()
        or keyword in b.author.lower()
        or keyword in b.category.lower()
    ]
    if not results:
        print("No matching books found.")
    else:
        for b in results:
            print(b)


def update_book() -> None:
    print("\n--- Update Book ---")
    book_id = input("Enter Book ID to update: ").strip()
    book = books.get(book_id)
    if not book:
        print("Book not found.")
        return

    print("Leave any field blank to keep existing value.")
    new_title = input(f"Title [{book.title}]: ").strip()
    new_author = input(f"Author [{book.author}]: ").strip()
    new_category = input(f"Category [{book.category}]: ").strip()
    new_total_str = input(f"Total copies [{book.total_copies}]: ").strip()

    if new_title:
        book.title = new_title
    if new_author:
        book.author = new_author
    if new_category:
        book.category = new_category
    if new_total_str:
        try:
            new_total = int(new_total_str)
            if new_total < len(book_id):
                pass
            if new_total < (book.total_copies - book.available_copies):
                print("Cannot reduce below number of currently issued copies.")
            else:
                diff = new_total - book.total_copies
                book.total_copies = new_total
                book.available_copies += diff
        except ValueError:
            print("Invalid total copies. Keeping old value.")

    print("Book updated:", book)


# ----------------- MEMBER FUNCTIONS -----------------
def register_member() -> None:
    print("\n--- Register Member ---")
    member_id = input("Enter Member ID: ").strip()
    if member_id in members:
        print("Member ID already exists.")
        return
    name = input("Enter Name: ").strip()
    phone = input("Enter Phone: ").strip()

    members[member_id] = Member(member_id=member_id, name=name, phone=phone)
    print("Member registered successfully.")


def view_all_members() -> None:
    print("\n--- All Members ---")
    if not members:
        print("No members registered.")
        return
    for m in members.values():
        print(m)


def search_member_by_id() -> None:
    print("\n--- Search Member ---")
    member_id = input("Enter Member ID: ").strip()
    member = members.get(member_id)
    if not member:
        print("Member not found.")
        return
    print(member)
    if member.borrowed_books:
        print("Borrowed books:", ", ".join(member.borrowed_books))
    else:
        print("No books currently borrowed.")


# ----------------- ISSUE / RETURN FUNCTIONS -----------------
def issue_book() -> None:
    global next_issue_id
    print("\n--- Issue Book ---")
    book_id = input("Enter Book ID: ").strip()
    member_id = input("Enter Member ID: ").strip()

    book = books.get(book_id)
    member = members.get(member_id)

    if not book:
        print("Book not found.")
        return
    if not member:
        print("Member not found.")
        return

    check_and_update_block_status(member)
    if member.blocked:
        print("Member is BLOCKED due to high outstanding fines.")
        return
    if book.available_copies <= 0:
        print("No available copies to issue.")
        return

    issue_date = datetime.today()
    due_date = issue_date + timedelta(days=ISSUE_DAYS)

    record = IssueRecord(
        issue_id=next_issue_id,
        book_id=book_id,
        member_id=member_id,
        issue_date=issue_date,
        due_date=due_date,
    )
    issues[next_issue_id] = record
    next_issue_id += 1

    book.available_copies -= 1
    member.borrowed_books.append(book_id)

    print("Book issued successfully.")
    print(f"Due date: {due_date.strftime(DATE_FORMAT)}")
    print(record)


def return_book() -> None:
    print("\n--- Return Book ---")
    issue_id_str = input("Enter Issue ID: ").strip()
    if not issue_id_str.isdigit():
        print("Issue ID must be a number.")
        return
    issue_id = int(issue_id_str)
    record = issues.get(issue_id)

    if not record:
        print("Issue record not found.")
        return
    if record.return_date:
        print("Book already returned.")
        return

    book = books.get(record.book_id)
    member = members.get(record.member_id)

    if not book or not member:
        print("Book or Member record missing. Cannot proceed safely.")
        return

    return_date = datetime.today()
    record.return_date = return_date

    late_days = record.days_late(return_date)
    fine = late_days * FINE_PER_DAY
    record.fine_charged = fine

    member.outstanding_fine += fine
    check_and_update_block_status(member)

    # update book & member
    book.available_copies += 1
    if record.book_id in member.borrowed_books:
        member.borrowed_books.remove(record.book_id)

    print("Book return recorded.")
    print(f"Late days: {late_days}, Fine charged: ₹{fine}")
    print(f"Member outstanding fine now: ₹{member.outstanding_fine}")
    if member.blocked:
        print("Member is now BLOCKED due to high fines.")


# ----------------- REPORTS & REMINDERS -----------------
def view_active_issues() -> None:
    print("\n--- Active Issues (Not Returned) ---")
    active = [r for r in issues.values() if r.return_date is None]
    if not active:
        print("No active issues.")
        return
    for r in active:
        print(r)


def view_issue_history() -> None:
    print("\n--- All Issue Records (History) ---")
    if not issues:
        print("No issue records.")
        return
    for r in issues.values():
        print(r)


def show_due_and_overdue_reminders() -> None:
    print("\n--- Due / Overdue Reminders ---")
    today = datetime.today()
    any_found = False

    for r in issues.values():
        if r.return_date is not None:
            continue

        days_to_due = (r.due_date.date() - today.date()).days
        member = members.get(r.member_id)
        book = books.get(r.book_id)
        member_name = member.name if member else "Unknown"
        book_title = book.title if book else "Unknown"

        if days_to_due < 0:
            any_found = True
            print(
                f"[OVERDUE] IssueID {r.issue_id} | Book: {book_title} "
                f"| Member: {member_name} | Due: {r.due_date.strftime(DATE_FORMAT)} "
                f"| Late by {-days_to_due} day(s)"
            )
        elif days_to_due <= 2:
            any_found = True
            print(
                f"[DUE SOON] IssueID {r.issue_id} | Book: {book_title} "
                f"| Member: {member_name} | Due in {days_to_due} day(s) "
                f"on {r.due_date.strftime(DATE_FORMAT)}"
            )

    if not any_found:
        print("No books are due soon or overdue.")


# ----------------- PDF EXPORT -----------------
def export_pdf_report() -> None:
    print("\n--- Export PDF Report ---")
    filename = input("Enter output filename (default: library_report.pdf): ").strip()
    if not filename:
        filename = "library_report.pdf"
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        print("The 'reportlab' library is not installed.")
        print("Install it with: pip install reportlab")
        return

    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Library Borrowing Summary & Fines")
    y -= 30

    c.setFont("Helvetica", 10)
    today_str = datetime.today().strftime(DATE_FORMAT)
    c.drawString(50, y, f"Generated on: {today_str}")
    y -= 30

    # Active Issues
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Active Issues:")
    y -= 20
    c.setFont("Helvetica", 9)
    active = [r for r in issues.values() if r.return_date is None]
    if not active:
        c.drawString(60, y, "No active issues.")
        y -= 15
    else:
        for r in active:
            if y < 80:
                c.showPage()
                y = height - 50
            member = members.get(r.member_id)
            book = books.get(r.book_id)
            line = (
                f"ID {r.issue_id} | Book: {book.title if book else r.book_id} | "
                f"Member: {member.name if member else r.member_id} | "
                f"Due: {r.due_date.strftime(DATE_FORMAT)}"
            )
            c.drawString(60, y, line)
            y -= 12

    # Members & Fines
    if y < 120:
        c.showPage()
        y = height - 50

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Members & Outstanding Fines:")
    y -= 20
    c.setFont("Helvetica", 9)
    if not members:
        c.drawString(60, y, "No members.")
        y -= 15
    else:
        for m in members.values():
            if y < 80:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica-Bold", 12)
                c.drawString(50, y, "Members & Outstanding Fines (contd.):")
                y -= 20
                c.setFont("Helvetica", 9)
            line = (
                f"{m.member_id} - {m.name} | Phone: {m.phone} | "
                f"Fine: ₹{m.outstanding_fine} | Status: {'BLOCKED' if m.blocked else 'ACTIVE'}"
            )
            c.drawString(60, y, line)
            y -= 12

    c.save()
    print(f"PDF report saved as '{filename}'.")


# ----------------- MAIN MENU -----------------
def show_menu() -> None:
    print("\n========== Library Management & Fine System ==========")
    print("1.  Add Book")
    print("2.  View All Books")
    print("3.  Search Books")
    print("4.  Update Book")
    print("5.  Register Member")
    print("6.  View All Members")
    print("7.  Search Member by ID")
    print("8.  Issue Book")
    print("9.  Return Book")
    print("10. View Active Issues")
    print("11. View Issue History")
    print("12. Show Due/Overdue Reminders")
    print("13. Export PDF Report")
    print("0.  Exit")


def main() -> None:
    while True:
        show_menu()
        choice = input("Enter choice: ").strip()

        if choice == "1":
            add_book()
            pause()
        elif choice == "2":
            view_all_books()
            pause()
        elif choice == "3":
            search_books()
            pause()
        elif choice == "4":
            update_book()
            pause()
        elif choice == "5":
            register_member()
            pause()
        elif choice == "6":
            view_all_members()
            pause()
        elif choice == "7":
            search_member_by_id()
            pause()
        elif choice == "8":
            issue_book()
            pause()
        elif choice == "9":
            return_book()
            pause()
        elif choice == "10":
            view_active_issues()
            pause()
        elif choice == "11":
            view_issue_history()
            pause()
        elif choice == "12":
            show_due_and_overdue_reminders()
            pause()
        elif choice == "13":
            export_pdf_report()
            pause()
        elif choice == "0":
            print("Exiting Library Management System. Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")
            pause()


if __name__ == "__main__":
    main()

