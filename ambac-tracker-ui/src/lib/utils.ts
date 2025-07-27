import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getCookie(name: string): string | undefined | null {
  const value = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)")
  return value ? value.pop() : null
}