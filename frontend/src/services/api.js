/**
 * Service API centralisé pour WoW Housing Price Tracker
 * Regroupe tous les appels backend pour faciliter la maintenance
 */

const API_BASE = '/api';

/**
 * Wrapper générique pour les appels fetch avec gestion d'erreur basique
 */
async function request(endpoint, options = {}) {
    const response = await fetch(`${API_BASE}${endpoint}`, options);
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `API Error: ${response.status} ${response.statusText}`);
    }
    return response.json();
}

/**
 * Wrapper avec auth token dans le header
 */
function authHeaders() {
    const token = localStorage.getItem('adminToken');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
}

export const api = {
    items: {
        /**
         * Récupère la liste paginée des items avec filtres
         * @param {Object} params - { realm_id, page, page_size, sort_by, sort_order, search, category }
         */
        list: (params) => {
            const searchParams = new URLSearchParams();
            Object.entries(params).forEach(([key, value]) => {
                if (value !== undefined && value !== null && value !== '') {
                    searchParams.append(key, value.toString());
                }
            });
            return request(`/items?${searchParams.toString()}`);
        },

        /**
         * Récupère les détails d'un item spécifique pour un royaume donné
         */
        getDetails: (itemId, realmId) => {
            return request(`/items/${itemId}?realm_id=${realmId}`);
        },

        /**
         * Récupère la liste des catégories d'items
         */
        getCategories: () => {
            return request('/items/categories');
        },

        /**
         * Récupère les prix d'un item sur tous les royaumes
         */
        getRealmPrices: (itemId) => {
            return request(`/items/${itemId}/realms`);
        }
    },

    prices: {
        /**
         * Récupère les meilleurs serveurs pour vendre un item
         */
        getBestServers: (realmId, itemId) => {
            return request(`/prices/${realmId}/${itemId}/best-servers`);
        }
    },

    realms: {
        /**
         * Liste tous les royaumes supportés
         */
        getAll: () => {
            return request('/realms');
        }
    },

    update: {
        /**
         * Récupère le statut actuel de la mise à jour (public)
         */
        getStatus: () => {
            return request('/update/status');
        },

        /**
         * Lance une mise à jour des données (admin only)
         * @param {Object} params - { force, priority_realm_id }
         */
        start: (params = {}) => {
            const searchParams = new URLSearchParams();
            if (params.force) searchParams.append('force', 'true');
            if (params.priority_realm_id) searchParams.append('priority_realm_id', params.priority_realm_id);

            return request(`/update/start?${searchParams.toString()}`, {
                method: 'POST',
                headers: authHeaders()
            });
        },

        /**
         * Force la re-synchronisation des recettes (admin only)
         */
        syncRecipes: () => {
            return request('/update/sync-recipes', {
                method: 'POST',
                headers: authHeaders()
            });
        }
    },

    auth: {
        /**
         * Login admin
         */
        login: (password) => {
            return request('/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password })
            });
        },

        /**
         * Vérifier un token
         */
        verify: (token) => {
            return request('/auth/verify', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
        }
    }
};
