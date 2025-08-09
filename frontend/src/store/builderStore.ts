import { create } from "zustand"
import { modelRegistry } from "../components/3d/modelRegistry"

interface Transform {
  scale?: [number, number, number]
  position?: [number, number, number]
  rotation?: [number, number, number]
}

interface Component {
  id: string
  name: string
  category: string
  price: number
  model?: string
  transform?: Transform
}

interface BuilderState {
  selectedComponents: Record<string, Component | null>
  selectComponent: (category: string, component: Component) => void
  removeComponent: (category: string) => void
  getTotalPrice: () => number
}

export const useBuilderStore = create<BuilderState>((set, get) => ({
  selectedComponents: {
    cpu: null,
    gpu: null,
    motherboard: null,
    memory: null,
    storage: null,
    psu: null,
    case: null,
    cooling: null,
  },
  selectComponent: (category: string, component: Component) => {

    const withModel: Component = {
      ...component,
      model: component.model || modelRegistry[category]?.url,
      transform: component.transform,
    }

    set((state) => ({
      selectedComponents: {
        ...state.selectedComponents,
        [category]: withModel,
      },
    }))
  },
  removeComponent: (category: string) => {
    set((state) => ({
      selectedComponents: {
        ...state.selectedComponents,
        [category]: null,
      },
    }))
  },
  getTotalPrice: () => {
    const { selectedComponents } = get()
    return Object.values(selectedComponents).reduce((total, component) => total + (component?.price || 0), 0)
  },
}))
