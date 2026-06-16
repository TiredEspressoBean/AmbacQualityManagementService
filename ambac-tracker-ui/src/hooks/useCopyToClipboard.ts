import { useState } from "react";

/**
 * Copy a string to the clipboard and briefly flag success.
 *
 * `isCopied` flips true on a successful write and resets after
 * `copiedDuration` ms — handy for swapping a copy icon to a checkmark.
 */
export function useCopyToClipboard({
  copiedDuration = 3000,
}: {
  copiedDuration?: number;
} = {}) {
  const [isCopied, setIsCopied] = useState<boolean>(false);

  const copyToClipboard = (value: string) => {
    if (!value) return;

    navigator.clipboard.writeText(value).then(() => {
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), copiedDuration);
    });
  };

  return { isCopied, copyToClipboard };
}
