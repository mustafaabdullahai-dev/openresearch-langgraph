import { useCallback, useEffect, useState } from "react";

export function useDarkMode() {
  const [dark, setDark] = useState<boolean>(() => {
    const stored = localStorage.getItem("theme");
    if (stored) return stored === "dark";
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  const toggle = useCallback(() => {
    setDark((prev) => {
      localStorage.setItem("theme", prev ? "light" : "dark");
      return !prev;
    });
  }, []);

  return { dark, toggle };
}