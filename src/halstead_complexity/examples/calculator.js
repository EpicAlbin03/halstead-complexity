/**
 * A calculator module with various operations to test Halstead metrics.
 * This includes classes, functions, loops, conditionals, and string operations.
 */

class Calculator {
  /**
   * Constructor for Calculator class.
   * @param {string} name - The name of the calculator
   */
  constructor(name = "Calculator") {
    this.name = name
    this.history = []
    this.memory = 0.0
  }

  /**
   * Add two numbers.
   * @param {number} a - First number
   * @param {number} b - Second number
   * @returns {number} The sum
   */
  add(a, b) {
    const result = a + b
    this.history.push(`${a} + ${b} = ${result}`)
    return result
  }

  /**
   * Subtract b from a.
   * @param {number} a - First number
   * @param {number} b - Second number
   * @returns {number} The difference
   */
  subtract(a, b) {
    const result = a - b
    this.history.push(`${a} - ${b} = ${result}`)
    return result
  }

  /**
   * Multiply two numbers.
   * @param {number} a - First number
   * @param {number} b - Second number
   * @returns {number} The product
   */
  multiply(a, b) {
    const result = a * b
    this.history.push(`${a} * ${b} = ${result}`)
    return result
  }

  /**
   * Divide a by b.
   * @param {number} a - Numerator
   * @param {number} b - Denominator
   * @returns {number} The quotient
   */
  divide(a, b) {
    if (b === 0) {
      throw new Error("Cannot divide by zero")
    }
    const result = a / b
    this.history.push(`${a} / ${b} = ${result}`)
    return result
  }

  /**
   * Calculate base raised to exponent.
   * @param {number} base - The base number
   * @param {number} exponent - The exponent
   * @returns {number} The power result
   */
  power(base, exponent) {
    const result = Math.pow(base, exponent)
    this.history.push(`${base} ** ${exponent} = ${result}`)
    return result
  }

  /**
   * Calculate a modulo b.
   * @param {number} a - The dividend
   * @param {number} b - The divisor
   * @returns {number} The remainder
   */
  modulo(a, b) {
    const result = a % b
    this.history.push(`${a} % ${b} = ${result}`)
    return result
  }

  /**
   * Store a value in memory.
   * @param {number} value - Value to store
   */
  storeMemory(value) {
    this.memory = value
    console.log(`Stored ${value} in memory`)
  }

  /**
   * Recall value from memory.
   * @returns {number} The stored value
   */
  recallMemory() {
    return this.memory
  }

  /**
   * Clear memory.
   */
  clearMemory() {
    this.memory = 0.0
  }

  /**
   * Get calculation history.
   * @returns {Array<string>} Copy of history
   */
  getHistory() {
    return [...this.history]
  }

  /**
   * Clear calculation history.
   */
  clearHistory() {
    this.history = []
  }
}

/**
 * Calculate factorial of n using recursion.
 * @param {number} n - The number
 * @returns {number} The factorial
 */
function factorial(n) {
  if (n < 0) {
    throw new Error("Factorial not defined for negative numbers")
  }
  if (n === 0 || n === 1) {
    return 1
  }
  return n * factorial(n - 1)
}

/**
 * Generate Fibonacci sequence up to n terms.
 * @param {number} n - Number of terms
 * @returns {Array<number>} The Fibonacci sequence
 */
function fibonacci(n) {
  if (n <= 0) {
    return []
  } else if (n === 1) {
    return [0]
  }

  const sequence = [0, 1]
  for (let i = 2; i < n; i++) {
    const nextNum = sequence[i - 1] + sequence[i - 2]
    sequence.push(nextNum)
  }

  return sequence
}

/**
 * Check if a number is prime.
 * @param {number} n - The number to check
 * @returns {boolean} True if prime, false otherwise
 */
function isPrime(n) {
  if (n < 2) {
    return false
  }
  if (n === 2) {
    return true
  }
  if (n % 2 === 0) {
    return false
  }

  for (let i = 3; i <= Math.sqrt(n); i += 2) {
    if (n % i === 0) {
      return false
    }
  }

  return true
}

/**
 * Find all prime numbers up to limit.
 * @param {number} limit - The upper limit
 * @returns {Array<number>} Array of prime numbers
 */
function findPrimes(limit) {
  const primes = []
  for (let num = 2; num <= limit; num++) {
    if (isPrime(num)) {
      primes.push(num)
    }
  }
  return primes
}

/**
 * Calculate basic statistics for an array of numbers.
 * @param {Array<number>} numbers - Array of numbers
 * @returns {Object} Statistics object
 */
function statistics(numbers) {
  if (!numbers || numbers.length === 0) {
    return { count: 0, sum: 0.0, mean: 0.0, min: 0.0, max: 0.0 }
  }

  const total = numbers.reduce((sum, num) => sum + num, 0)
  const count = numbers.length
  const mean = total / count
  const minimum = Math.min(...numbers)
  const maximum = Math.max(...numbers)

  // Calculate variance and standard deviation
  const variance = numbers.reduce((sum, x) => sum + Math.pow(x - mean, 2), 0) / count
  const stdDev = Math.sqrt(variance)

  return {
    count: count,
    sum: total,
    mean: mean,
    min: minimum,
    max: maximum,
    variance: variance,
    stdDev: stdDev,
  }
}

/**
 * Format calculation result as string.
 * @param {string} operation - The operation name
 * @param {number} result - The result value
 * @param {number} precision - Decimal precision
 * @returns {string} Formatted string
 */
function formatResult(operation, result, precision = 2) {
  if (precision < 0) {
    precision = 0
  }

  const formatted = result.toFixed(precision)
  return `Operation: ${operation}, Result: ${formatted}`
}

/**
 * Main function to demonstrate calculator usage.
 */
function main() {
  const calc = new Calculator("MyCalc")

  console.log(`Calculator: ${calc.name}`)
  console.log("-".repeat(40))

  // Basic operations
  const result1 = calc.add(10, 5)
  const result2 = calc.multiply(result1, 2)
  const result3 = calc.divide(result2, 3)

  console.log(`Results: ${result1}, ${result2}, ${result3.toFixed(2)}`)

  // Test factorial
  try {
    const fact5 = factorial(5)
    console.log(`Factorial of 5: ${fact5}`)
  } catch (e) {
    console.log(`Error: ${e.message}`)
  }

  // Test Fibonacci
  const fibSeq = fibonacci(10)
  console.log(`Fibonacci sequence: ${fibSeq}`)

  // Test prime numbers
  const primes = findPrimes(20)
  console.log(`Primes up to 20: ${primes}`)

  // Test statistics
  const data = [1.5, 2.7, 3.2, 4.8, 5.1]
  const stats = statistics(data)
  console.log(`Statistics: mean=${stats.mean.toFixed(2)}, stdDev=${stats.stdDev.toFixed(2)}`)

  // Show history
  const history = calc.getHistory()
  console.log("\nCalculation History:")
  for (const entry of history) {
    console.log(`  ${entry}`)
  }
}

// Run main if this is the main module
if (typeof require !== "undefined" && require.main === module) {
  main()
}

module.exports = { Calculator, factorial, fibonacci, isPrime, findPrimes, statistics, formatResult }
