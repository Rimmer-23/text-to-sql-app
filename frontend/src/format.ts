export function plural(count: number, noun: string): string {
  return `${count.toLocaleString("en-US")} ${count === 1 ? noun : `${noun}s`}`;
}
