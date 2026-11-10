"use client";

/**
 * NEAR Wallet Selector, loaded in the browser only (dynamic imports on first use, so neither the selector nor its
 * modal CSS reaches the server bundle or pages that never open it). Mainnet, no contractId: signing in creates no
 * function-call access key, so every `set` is a full transaction the wallet asks the user to approve.
 */
import type { WalletSelector } from "@near-wallet-selector/core";
import type { WalletSelectorModal } from "@near-wallet-selector/modal-ui";

export interface WalletHandle {
  selector: WalletSelector;
  modal: WalletSelectorModal;
}

let handle: Promise<WalletHandle> | null = null;

export function loadWallet(): Promise<WalletHandle> {
  if (typeof window === "undefined") return Promise.reject(new Error("the wallet selector runs in the browser only"));
  if (!handle) {
    handle = (async () => {
      const [core, modalUi, mnw, meteor, here, intear] = await Promise.all([
        import("@near-wallet-selector/core"),
        import("@near-wallet-selector/modal-ui"),
        import("@near-wallet-selector/my-near-wallet"),
        import("@near-wallet-selector/meteor-wallet"),
        import("@near-wallet-selector/here-wallet"),
        import("@near-wallet-selector/intear-wallet"),
        import("./nearWalletStyles"),
      ]);
      const selector = await core.setupWalletSelector({
        network: "mainnet",
        modules: [mnw.setupMyNearWallet(), meteor.setupMeteorWallet(), here.setupHereWallet(), intear.setupIntearWallet()],
      });
      const modal = modalUi.setupModal(selector, { theme: "light", description: "Connect a NEAR account to publish a Valuo forecast to SocialDB (social.near) under that account." });
      return { selector, modal };
    })().catch((e) => {
      handle = null;
      throw e;
    });
  }
  return handle;
}

/** Active account id, or null. */
export function activeAccountId(selector: WalletSelector): string | null {
  const accounts = selector.store.getState().accounts;
  return accounts.find((a) => a.active)?.accountId ?? accounts[0]?.accountId ?? null;
}

/** Transaction hash from a FinalExecutionOutcome-like object (shape differs slightly across wallets). */
export function txHashOf(outcome: unknown): string | null {
  if (!outcome || typeof outcome !== "object") return null;
  const o = outcome as { transaction?: { hash?: unknown }; transaction_outcome?: { id?: unknown } };
  const h = o.transaction?.hash ?? o.transaction_outcome?.id;
  return typeof h === "string" && /^[1-9A-HJ-NP-Za-km-z]{32,64}$/.test(h) ? h : null;
}

/** First failure message in an outcome (status.Failure on the tx or any receipt), or null when it succeeded. */
export function failureOf(outcome: unknown): string | null {
  if (!outcome || typeof outcome !== "object") return null;
  const o = outcome as { status?: unknown; receipts_outcome?: { outcome?: { status?: unknown } }[] };
  const statuses = [o.status, ...(o.receipts_outcome ?? []).map((r) => r.outcome?.status)];
  for (const s of statuses) {
    if (s && typeof s === "object" && "Failure" in (s as Record<string, unknown>)) return JSON.stringify((s as Record<string, unknown>).Failure).slice(0, 400);
  }
  return null;
}
