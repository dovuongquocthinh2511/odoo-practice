/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { symmetricalDifference } from "@web/core/utils/arrays";
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";

// Helper functions
function parseBranchIds(bidsFromHash) {
    const bids = [];
    if (typeof bidsFromHash === "string") {
        bids.push(...bidsFromHash.split(",").map(Number));
    } else if (typeof bidsFromHash === "number") {
        bids.push(bidsFromHash);
    }
    return bids;
}

function computeAllowedBranchIds(bids) {
    const { user_branches } = session;
    let allowedBranchIds = bids || [];
    const availableBranchesFromSession = user_branches.allowed_branches;

    const notReallyAllowedBranches = allowedBranchIds.filter(
        (id) => !(id in availableBranchesFromSession)
    );
    if (!allowedBranchIds.length || notReallyAllowedBranches.length) {
        allowedBranchIds = [user_branches.current_branch];
    }
    return allowedBranchIds;
}

// Branch service definition
export const branchService = {
    dependencies: ["company"],
    start(env, { company }) {
        let bids;
        var list = [];
        var dict = {};

        const router = env.services.router;
        const cookie = env.services.cookie;
        const user = env.services.user;

        if (router && router.current && "bids" in router.current.hash) {
            bids = parseBranchIds(router.current.hash.bids);
        } else if (cookie && cookie.current && "bids" in cookie.current) {
            bids = parseBranchIds(cookie.current.bids);
        }
        let allowedBranchIds = computeAllowedBranchIds(bids);

        const stringBIds = allowedBranchIds.join(",");
        if (router) {
            router.replaceState({ bids: stringBIds }, { lock: true });
        }
        if (cookie) {
            cookie.setCookie("bids", stringBIds);
        }

        if (user) {
            user.updateContext({ allowed_branch_ids: allowedBranchIds });
        }

        const availableBranches = session.user_branches.allowed_branches;
        const { user_companies } = session;
        const availablecompany = company.allowedCompanies;

        for (const [key, value] of Object.entries(availableBranches)) {
            for (const [key1, value1] of Object.entries(availablecompany)) {
                if(value['company'] === value1){
                    dict[key] = value
                }
            }
        }
        list.push(dict)

        return {
            availableBranches,
            get allowedBranchIds() {
                return allowedBranchIds.slice();
            },
            get currentBranch() {
                return availableBranches[allowedBranchIds[0]];
            },
            setBranches(mode, ...branchIds) {
                // compute next branch ids
                let nextBranchIds;
                if (mode === "toggle") {
                    nextBranchIds = symmetricalDifference(allowedBranchIds, branchIds);
                } else if (mode === "loginto") {
                    const branchId = branchIds[0];
                    if (allowedBranchIds.length === 1) {
                        // 1 enabled branch: stay in single branch mode
                        nextBranchIds = [branchId];
                    } else {
                        // multi branch mode
                        nextBranchIds = [
                            branchId,
                            ...allowedBranchIds.filter((id) => id !== branchId),
                        ];
                    }
                }
                let branchId = nextBranchIds.reverse();
                nextBranchIds = branchId.length ? branchId : [branchIds[0]];
                // apply them
                if (router) {
                    router.pushState({ bids: nextBranchIds }, { lock: true });
                }
                if (cookie) {
                    cookie.setCookie("bids", nextBranchIds);
                }
                rpc("/set_branch", {
                    BranchID: nextBranchIds,
                });
                browser.setTimeout(() => browser.location.reload()); // history.pushState is a little async
            },
        };
    },
};

// Register the service
registry.category("services").add("branch", branchService);