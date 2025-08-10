"use client";

import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  LogOut,
  Eye,
  Cpu,
  Monitor,
  HardDrive,
  Zap,
  Settings,
  MemoryStick,
  CircuitBoardIcon as Motherboard,
  Fan,
  Server,
  CheckCircle,
  XCircle,
} from "lucide-react";
import { useAuthStore } from "../store/authStore";
import { useBuilderStore } from "../store/builderStore";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import axios from "axios";

// Map category to API endpoint and icon
const CATEGORY_CONFIG: Record<
  string,
  { endpoint: string; icon: React.ReactNode; label: string }
> = {
  case: {
    endpoint: "/api/v1/cases/",
    icon: <Settings className="w-6 h-6" />,
    label: "Case",
  },
  motherboard: {
    endpoint: "/api/v1/motherboards/",
    icon: <Motherboard className="w-6 h-6" />,
    label: "Motherboard",
  },
  cpu: {
    endpoint: "/api/v1/cpus/",
    icon: <Cpu className="w-6 h-6" />,
    label: "Processor",
  },
  gpu: {
    endpoint: "/api/v1/gpus/",
    icon: <Monitor className="w-6 h-6" />,
    label: "Graphics Card",
  },
  psu: {
    endpoint: "/api/v1/power-supplies/",
    icon: <Zap className="w-6 h-6" />,
    label: "Power Supply",
  },
  cooling: {
    endpoint: "/api/v1/cpu-coolers/",
    icon: <Fan className="w-6 h-6" />,
    label: "Cooling",
  },
  memory: {
    endpoint: "/api/v1/ram/",
    icon: <MemoryStick className="w-6 h-6" />,
    label: "Memory",
  },
  storage: {
    endpoint: "/api/v1/storage/",
    icon: <HardDrive className="w-6 h-6" />,
    label: "Storage",
  },
};

// Map UI categories to backend compatibility types
const COMPAT_TYPE_MAP: Record<string, string> = {
  memory: "ram",
  cooling: "cooler",
  cpu: "cpu",
  motherboard: "motherboard",
  gpu: "gpu",
  storage: "storage",
  psu: "psu",
  case: "case",
};

// The new desired order
const CATEGORY_ORDER = [
  "case",
  "motherboard",
  "cpu",
  "gpu",
  "psu",
  "cooling",
  "memory",
  "storage",
];

type Item = {
  id: number;
  name: string;
  model?: string;
  price: number;
  compatible?: boolean;
};

const BuilderPage = () => {
  const { user, logout, fetchUser } = useAuthStore();
  const {
    selectedComponents,
    selectComponent,
    getTotalPrice,
    removeComponent,
  } = useBuilderStore();
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [itemsByCategory, setItemsByCategory] = useState<
    Record<string, Item[]>
  >({});
  const [loadingByCategory, setLoadingByCategory] = useState<
    Record<string, boolean>
  >({});

  useEffect(() => {
    if (!user) {
      fetchUser();
    }
  }, [user, fetchUser]);

  // Build query params for compatibility endpoint based on current selection
  const getSelectionQuery = () => {
    const q: Record<string, string | number> = {};
    const sc = selectedComponents as Record<string, { id?: number } | null>;
    if (sc.cpu?.id) q.selected_cpu_id = sc.cpu.id;
    if (sc.motherboard?.id) q.selected_motherboard_id = sc.motherboard.id;
    if (sc.memory?.id) q.selected_ram_id = sc.memory.id;
    if (sc.gpu?.id) q.selected_gpu_id = sc.gpu.id;
    if (sc.storage?.id) q.selected_storage_id = sc.storage.id;
    if (sc.psu?.id) q.selected_psu_id = sc.psu.id;
    if (sc.case?.id) q.selected_case_id = sc.case.id;
    if (sc.cooling?.id) q.selected_cooler_id = sc.cooling.id;
    return q;
  };

  // Fetch items with compatibility for a given category
  const fetchWithCompatibility = async (categoryId: string) => {
    const compatType = COMPAT_TYPE_MAP[categoryId] || categoryId;
    const params = new URLSearchParams({ type: compatType } as any);
    const sel = getSelectionQuery();
    Object.entries(sel).forEach(([k, v]) => params.append(k, String(v)));
    const res = await axios.get(
      `/api/v1/options-with-compatibility/?${params.toString()}`
    );
    const items: Item[] = (res.data || []).map((row: any) => ({
      id: row.id,
      name: row.name,
      model: row.model,
      price: Number(row.price ?? 0),
      compatible: Boolean(row.compatible),
    }));
    return items;
  };

  // Fetch items lazily when a category is expanded
  const ensureCategoryLoaded = async (categoryId: string, force = false) => {
    if (
      (itemsByCategory[categoryId] && !force) ||
      loadingByCategory[categoryId]
    )
      return;
    setLoadingByCategory((s) => ({ ...s, [categoryId]: true }));
    try {
      const items = await fetchWithCompatibility(categoryId);
      setItemsByCategory((s) => ({ ...s, [categoryId]: items }));
    } catch (e) {
      console.error(`Failed to fetch ${categoryId}`, e);
      setItemsByCategory((s) => ({ ...s, [categoryId]: [] }));
    } finally {
      setLoadingByCategory((s) => ({ ...s, [categoryId]: false }));
    }
  };

  // When selection changes and a category panel is open, refresh its compatibility
  useEffect(() => {
    if (selectedCategory) {
      ensureCategoryLoaded(selectedCategory, true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(selectedComponents), selectedCategory]);

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-black/90 backdrop-blur-sm border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center">
              <div className="w-6 h-6 bg-white rounded transform rotate-45"></div>
            </div>
            <div className="text-white font-bold text-xl">DREAM BUILDERS</div>
          </div>

          <div className="flex items-center space-x-4">
            <span className="text-gray-300 ">
              Welcome, {user?.username || "User"}
            </span>
            <Link to="/visualizer">
              <Button className="!bg-white hover:!bg-gray-50 !text-black border border-gray-300">
                <Eye className="w-4 h-4 mr-2" />
                3D Visualizer
              </Button>
            </Link>
            <Button
              onClick={logout}
              className="!bg-white hover:!bg-gray-50 !text-black border border-gray-300"
            >
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-4">PC Builder</h1>
          <p className="text-gray-400">
            Select components to build your perfect PC
          </p>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-4">
            {CATEGORY_ORDER.map((categoryId) => {
              const cfg = CATEGORY_CONFIG[categoryId];
              const selectedComponent = selectedComponents[categoryId];
              const items = itemsByCategory[categoryId] || [];
              const loading = !!loadingByCategory[categoryId];
              return (
                <Card
                  key={categoryId}
                  className={`bg-gray-900 border-gray-800 hover:border-gray-700 transition-all cursor-pointer ${
                    selectedCategory === categoryId ? "border-blue-500" : ""
                  }`}
                  onClick={async () => {
                    const next =
                      selectedCategory === categoryId ? null : categoryId;
                    setSelectedCategory(next);
                    if (next) await ensureCategoryLoaded(categoryId, true);
                  }}
                >
                  <div className="p-6">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4">
                        <div className="text-blue-400">{cfg.icon}</div>
                        <div>
                          <h3 className="text-lg font-semibold">{cfg.label}</h3>
                          <p className="text-gray-400 text-sm">
                            {selectedComponent
                              ? selectedComponent.name
                              : `Select ${cfg.label.toLowerCase()}`}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        {selectedComponent && (
                          <p className="text-lg font-semibold">
                            ${selectedComponent.price.toLocaleString()}
                          </p>
                        )}
                        <p className="text-sm text-gray-400">
                          {selectedComponent ? "Selected" : "Not selected"}
                        </p>
                      </div>
                    </div>

                    {selectedCategory === categoryId && (
                      <div className="mt-6 pt-6 border-t border-gray-800">
                        {loading ? (
                          <div className="flex items-center text-gray-400">
                            <Server className="w-4 h-4 mr-2 animate-pulse" />{" "}
                            Loading...
                          </div>
                        ) : (
                          <div className="space-y-3">
                            {items.map((component) => {
                              const isCompatible =
                                component.compatible !== false;
                              return (
                                <div
                                  key={`${categoryId}-${component.id}`}
                                  className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors ${
                                    isCompatible
                                      ? "bg-gray-800 hover:bg-gray-700"
                                      : "bg-gray-800/70 hover:bg-gray-700/70"
                                  }`}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    selectComponent(categoryId, {
                                      id: component.id.toString(),
                                      name: component.name,
                                      category: categoryId,
                                      price: component.price,
                                      model: component.model,
                                    });
                                    setSelectedCategory(null);
                                  }}
                                >
                                  <div>
                                    <p className="font-medium">
                                      {component.name}
                                    </p>
                                    {component.model && (
                                      <p className="text-sm text-gray-400">
                                        {component.model}
                                      </p>
                                    )}
                                  </div>
                                  <div className="flex items-center space-x-3">
                                    {isCompatible ? (
                                      <span className="flex items-center text-green-400 text-sm">
                                        <CheckCircle className="w-4 h-4 mr-1" />{" "}
                                        Compatible
                                      </span>
                                    ) : (
                                      <span className="flex items-center text-red-400 text-sm">
                                        <XCircle className="w-4 h-4 mr-1" />{" "}
                                        Incompatible
                                      </span>
                                    )}
                                    <p className="font-semibold">
                                      ${component.price.toLocaleString()}
                                    </p>
                                  </div>
                                </div>
                              );
                            })}
                            {items.length === 0 && (
                              <div className="text-gray-400 text-sm">
                                No options found.
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    {selectedComponent && (
                      <div className="mt-4">
                        <Button
                          variant="outline"
                          size="sm"
                          className="border-gray-700 text-emerald-900 hover:bg-gray-800 hover:text-black bg-transparent"
                          onClick={(e) => {
                            e.stopPropagation();
                            removeComponent(categoryId);
                          }}
                        >
                          Remove {cfg.label}
                        </Button>
                      </div>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>

          <div className="space-y-6">
            <Card className="bg-gray-900 border-gray-800 p-6 sticky top-6">
              <h3 className="text-xl font-semibold mb-4">Build Summary</h3>
              <div className="space-y-4">
                <div className="space-y-2">
                  {Object.entries(selectedComponents).map(
                    ([category, component]) => (
                      <div
                        key={category}
                        className="flex justify-between text-sm"
                      >
                        <span className="text-gray-300 capitalize">
                          {category}
                        </span>
                        <span>
                          {component
                            ? `$${component.price.toLocaleString()}`
                            : "-"}
                        </span>
                      </div>
                    )
                  )}
                </div>
                <div className="border-t border-gray-800 pt-4">
                  <div className="flex justify-between text-lg font-semibold">
                    <span>Total</span>
                    <span>${getTotalPrice().toLocaleString()}</span>
                  </div>
                </div>
                <div className="space-y-3">
                  <Link to="/visualizer">
                    <Button className="w-full !bg-white hover:!bg-gray-50 !text-black border border-gray-300">
                      <Eye className="w-4 h-4 mr-2" />
                      View in 3D
                    </Button>
                  </Link>
                  <Button
                    variant="outline"
                    className="w-full border-gray-700 text-emerald-900 hover:bg-gray-800 hover:text-black bg-transparent mt-4"
                  >
                    Save Build
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BuilderPage;
