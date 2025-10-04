"""
A calculator module with various operations to test Halstead metrics.
This includes functions, classes, loops, conditionals, and string operations.
"""


class Calculator:
    """A simple calculator with basic arithmetic operations."""

    def __init__(self, name: str = "Calculator"):
        self.name = name
        self.history: list[str] = []
        self.memory = 0.0

    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result

    def subtract(self, a: float, b: float) -> float:
        """Subtract b from a."""
        result = a - b
        self.history.append(f"{a} - {b} = {result}")
        return result

    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result

    def divide(self, a: float, b: float) -> float:
        """Divide a by b."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        result = a / b
        self.history.append(f"{a} / {b} = {result}")
        return result

    def power(self, base: float, exponent: float) -> float:
        """Calculate base raised to exponent."""
        result = base**exponent
        self.history.append(f"{base} ** {exponent} = {result}")
        return result

    def modulo(self, a: float, b: float) -> float:
        """Calculate a modulo b."""
        result = a % b
        self.history.append(f"{a} % {b} = {result}")
        return result

    def store_memory(self, value: float) -> None:
        """Store a value in memory."""
        self.memory = value
        print(f"Stored {value} in memory")

    def recall_memory(self) -> float:
        """Recall value from memory."""
        return self.memory

    def clear_memory(self) -> None:
        """Clear memory."""
        self.memory = 0.0

    def get_history(self) -> list[str]:
        """Get calculation history."""
        return self.history.copy()

    def clear_history(self) -> None:
        """Clear calculation history."""
        self.history.clear()


def factorial(n: int) -> int:
    """Calculate factorial of n using recursion."""
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n == 0 or n == 1:
        return 1
    return n * factorial(n - 1)


def fibonacci(n: int) -> list[int]:
    """Generate Fibonacci sequence up to n terms."""
    if n <= 0:
        return []
    elif n == 1:
        return [0]

    sequence = [0, 1]
    for i in range(2, n):
        next_num = sequence[i - 1] + sequence[i - 2]
        sequence.append(next_num)

    return sequence


def is_prime(n: int) -> bool:
    """Check if a number is prime."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False

    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False

    return True


def find_primes(limit: int) -> list[int]:
    """Find all prime numbers up to limit."""
    primes: list[int] = []
    for num in range(2, limit + 1):
        if is_prime(num):
            primes.append(num)
    return primes


def statistics(numbers: list[float]) -> dict[str, float]:
    """Calculate basic statistics for a list of numbers."""
    if not numbers:
        return {"count": 0, "sum": 0.0, "mean": 0.0, "min": 0.0, "max": 0.0}

    total = sum(numbers)
    count = len(numbers)
    mean = total / count
    minimum = min(numbers)
    maximum = max(numbers)

    # Calculate variance and standard deviation
    variance = sum((x - mean) ** 2 for x in numbers) / count
    std_dev = variance**0.5

    return {
        "count": count,
        "sum": total,
        "mean": mean,
        "min": minimum,
        "max": maximum,
        "variance": variance,
        "std_dev": std_dev,
    }


def format_result(operation: str, result: float, precision: int = 2) -> str:
    """Format calculation result as string."""
    if precision < 0:
        precision = 0

    formatted = f"{result:.{precision}f}"
    return f"Operation: {operation}, Result: {formatted}"


def main() -> None:
    """Main function to demonstrate calculator usage."""
    calc = Calculator("MyCalc")

    print(f"Calculator: {calc.name}")
    print("-" * 40)

    # Basic operations
    result1 = calc.add(10, 5)
    result2 = calc.multiply(result1, 2)
    result3 = calc.divide(result2, 3)

    print(f"Results: {result1}, {result2}, {result3:.2f}")

    # Test factorial
    try:
        fact5 = factorial(5)
        print(f"Factorial of 5: {fact5}")
    except ValueError as e:
        print(f"Error: {e}")

    # Test Fibonacci
    fib_seq = fibonacci(10)
    print(f"Fibonacci sequence: {fib_seq}")

    # Test prime numbers
    primes = find_primes(20)
    print(f"Primes up to 20: {primes}")

    # Test statistics
    data = [1.5, 2.7, 3.2, 4.8, 5.1]
    stats = statistics(data)
    print(f"Statistics: mean={stats['mean']:.2f}, std_dev={stats['std_dev']:.2f}")

    # Show history
    history = calc.get_history()
    print("\nCalculation History:")
    for entry in history:
        print(f"  {entry}")


if __name__ == "__main__":
    main()
