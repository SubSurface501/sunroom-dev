// sunroom-web/src/services/universeService.ts

import axios from 'axios';
import { getApiUrl } from '@/lib/utils';

const API_URL = getApiUrl();

// --- INTERFACES ---

export interface Archetype {
    name: string;
    description: string;
    system_anchor: string;
    prohibitions: string[];
    suggestions: string[];
}

export interface Universe {
    id: string;
    name: string;
    description?: string;
    active_epoch_id?: number | null;
    // TODO: Add archetype info
}

export interface UniverseCreateData {
    name: string;
    description?: string;
    // TODO: Add archetype and epoch data
}

export interface UniverseUpdateData {
    name?: string;
    description?: string;
    active_epoch_id?: number | null;
}

export interface Epoch {
    id: number;
    universe_id: string;
    name: string;
    archetype?: string;
    system_anchor?: string;
    prohibitions?: string[];
    seed_prose?: string;
    character_stances?: Record<string, any>;
    created_at?: string;
    updated_at?: string;
}

export interface EpochCreateData {
    name: string;
    archetype?: string;
    system_anchor?: string;
    prohibitions?: string[];
}

export interface EpochUpdateData {
    name?: string;
    archetype?: string;
    system_anchor?: string;
    prohibitions?: string[];
    seed_prose?: string;
    character_stances?: Record<string, any>;
}

export interface Atom {
    id: string;
    user_id: string;
    name: string;
    type: string;
    content?: string;
    metadata?: Record<string, any>;
    created_at?: string;
    created_at_source?: string;
    epoch_label?: string;
    original_author?: string;
    discovery_epoch_id?: number | null;
    universe_id?: string;
    storyline_id?: string;
    permanence?: string;
}


// --- FUNCTIONS ---

/**
 * Fetches the list of all available universe archetypes from the backend.
 * @returns A promise that resolves to an array of Archetype objects.
 */
export const getArchetypes = async (): Promise<Archetype[]> => {
    try {
        const response = await axios.get(`${API_URL}/api/v1/archetypes`);
        return response.data;
    } catch (error) {
        console.error("Failed to fetch archetypes:", error);
        return [];
    }
};

/**
 * Fetches all universes for the currently authenticated user.
 * @param token The user's JWT access token.
 * @returns A promise that resolves to an array of Universe objects.
 */
export const getUniverses = async (token: string): Promise<Universe[]> => {
    try {
        const response = await axios.get(`${API_URL}/api/v1/universes`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        return response.data;
    } catch (error) {
        console.error("Failed to fetch universes:", error);
        return [];
    }
};

/**
 * Creates a new universe for the currently authenticated user.
 * @param token The user's JWT access token.
 * @param universeData The data for the new universe.
 * @returns A promise that resolves to the newly created Universe object.
 */
export const createUniverse = async (token: string, universeData: UniverseCreateData): Promise<Universe> => {
    const response = await axios.post(`${API_URL}/api/v1/universes`, universeData, {
        headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
};

/**
 * Fetches a single universe by its ID for the currently authenticated user.
 * @param token The user's JWT access token.
 * @param universeId The ID of the universe to fetch.
 * @returns A promise that resolves to the Universe object.
 */
export const getUniverse = async (token: string, universeId: string): Promise<Universe> => {
    const response = await axios.get(`${API_URL}/api/v1/universes/${universeId}`, {
        headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
};

/**
 * Updates an existing universe for the currently authenticated user.
 * @param token The user's JWT access token.
 * @param universeId The ID of the universe to update.
 * @param updateData The data to update the universe with.
 * @returns A promise that resolves to the updated Universe object.
 */
export const updateUniverse = async (token: string, universeId: string, updateData: UniverseUpdateData): Promise<Universe> => {
    const response = await axios.patch(`${API_URL}/api/v1/universes/${universeId}`, updateData, {
        headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
};

/**
 * Fetches all epochs for a specific universe.
 * @param token The user's JWT access token.
 * @param universeId The ID of the universe whose epochs to fetch.
 * @returns A promise that resolves to an array of Epoch objects.
 */
export const getEpochs = async (token: string, universeId: string): Promise<Epoch[]> => {
    try {
        const response = await axios.get(`${API_URL}/api/v1/universes/${universeId}/epochs`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        return response.data;
    } catch (error) {
        console.error(`Failed to fetch epochs for universe ${universeId}:`, error);
        return [];
    }
};

/**
 * Creates a new epoch for a specific universe. (NOTE: Archetype for the epoch will be assigned by the backend based on the Universe's default or first epoch)
 * @param token The user's JWT access token.
 * @param universeId The ID of the universe to create the epoch for.
 * @param epochData The data for the new epoch.
 * @returns A promise that resolves to the newly created Epoch object.
 */
export const createEpoch = async (token: string, universeId: string, epochData: EpochCreateData): Promise<Epoch> => {
    const response = await axios.post(`${API_URL}/api/v1/universes/${universeId}/epochs`, epochData, {
        headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
};

/**
 * Updates an existing epoch.
 * @param token The user's JWT access token.
 * @param epochId The ID of the epoch to update.
 * @param updateData The data to update the epoch with.
 * @returns A promise that resolves to the updated Epoch object.
 */
export const updateEpoch = async (token: string, epochId: number, updateData: EpochUpdateData): Promise<Epoch> => {
    const response = await axios.patch(`${API_URL}/api/v1/epochs/${epochId}`, updateData, {
        headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
};

/**
 * Fetches the count of latent (hidden) atoms for a specific universe.
 * @param token The user's JWT access token.
 * @param universeId The ID of the universe to check.
 * @returns A promise that resolves to an object containing the latent atom count.
 */
export const getLatentAtomCount = async (token: string, universeId: string): Promise<{ universe_id: string; latent_atom_count: number }> => {
    try {
        const response = await axios.get(`${API_URL}/api/v1/universes/${universeId}/latent-knowledge`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        return response.data;
    } catch (error) {
        console.error(`Failed to fetch latent atom count for universe ${universeId}:`, error);
        return { universe_id: universeId, latent_atom_count: 0 };
    }
};

/**
 * Fetches all atoms for a specific universe.
 * @param token The user's JWT access token.
 * @param universeId The ID of the universe whose atoms to fetch.
 * @returns A promise that resolves to an array of Atom objects.
 */
export const getAtomsForUniverse = async (token: string, universeId: string): Promise<Atom[]> => {
    try {
        const response = await axios.get(`${API_URL}/api/v1/universes/${universeId}/atoms`, {
            headers: { Authorization: `Bearer ${token}` }
        });
        return response.data;
    } catch (error) {
        console.error(`Failed to fetch atoms for universe ${universeId}:`, error);
        return [];
    }
};

/**
 * Unlocks a specific atom by setting its discovery_epoch_id to the current active epoch.
 * @param token The user's JWT access token.
 * @param atomId The ID of the atom to unlock.
 * @param activeEpochId The ID of the currently active epoch in the universe.
 * @returns A promise that resolves to the updated Atom object.
 */
export const unlockAtom = async (token: string, atomId: string, activeEpochId: number): Promise<Atom> => {
    const response = await axios.patch(`${API_URL}/api/v1/atoms/${atomId}/unlock`, { discovery_epoch_id: activeEpochId }, {
        headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
};
