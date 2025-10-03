function isOdd(n) {
  if (n % 2 !== 0) {
    console.log(`${n} is odd.`)
    return true
  } else {
    console.log(`${n} is not odd.`)
    return false
  }
}

// Example usage
isOdd(5)
isOdd(8)
