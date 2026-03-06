import { create } from 'zustand';
import type { Pedido, CreateDetallePedido } from '@/types';

interface PedidoDraft {
  cliente_ruc: string;
  cliente_razon_social: string;
  representante: string;
  condicion_pago: string;
  detalles: CreateDetallePedido[];
}

interface PedidoState {
  pedidos: Pedido[];
  selectedPedido: Pedido | null;
  draft: PedidoDraft;
  isLoading: boolean;
  setPedidos: (pedidos: Pedido[]) => void;
  setSelectedPedido: (pedido: Pedido | null) => void;
  updateDraft: (partial: Partial<PedidoDraft>) => void;
  addDetalle: (detalle: CreateDetallePedido) => void;
  removeDetalle: (index: number) => void;
  updateDetalle: (index: number, detalle: Partial<CreateDetallePedido>) => void;
  resetDraft: () => void;
  setLoading: (loading: boolean) => void;
}

const emptyDraft: PedidoDraft = {
  cliente_ruc: '',
  cliente_razon_social: '',
  representante: '',
  condicion_pago: '',
  detalles: [],
};

export const usePedidoStore = create<PedidoState>((set) => ({
  pedidos: [],
  selectedPedido: null,
  draft: { ...emptyDraft },
  isLoading: false,

  setPedidos: (pedidos) => set({ pedidos }),
  setSelectedPedido: (pedido) => set({ selectedPedido: pedido }),

  updateDraft: (partial) =>
    set((state) => ({
      draft: { ...state.draft, ...partial },
    })),

  addDetalle: (detalle) =>
    set((state) => ({
      draft: {
        ...state.draft,
        detalles: [...state.draft.detalles, detalle],
      },
    })),

  removeDetalle: (index) =>
    set((state) => ({
      draft: {
        ...state.draft,
        detalles: state.draft.detalles.filter((_, i) => i !== index),
      },
    })),

  updateDetalle: (index, detalle) =>
    set((state) => ({
      draft: {
        ...state.draft,
        detalles: state.draft.detalles.map((d, i) =>
          i === index ? { ...d, ...detalle } : d
        ),
      },
    })),

  resetDraft: () => set({ draft: { ...emptyDraft } }),
  setLoading: (isLoading) => set({ isLoading }),
}));
