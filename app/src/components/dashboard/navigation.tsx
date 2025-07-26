"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Cloud, BarChart3, Home, Menu, X, Settings } from "lucide-react";

export function Navigation() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [currentTime, setCurrentTime] = useState<string>("");

  useEffect(() => {
    // Set initial time
    const updateTime = () => {
      const time = new Date().toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
      });
      setCurrentTime(time);
    };

    updateTime(); // Set initial time
    const interval = setInterval(updateTime, 1000); // Update every second

    return () => clearInterval(interval);
  }, []);

  return (
    <>
      {/* Floating Navigation */}
      <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50 w-full max-w-4xl px-4">
        <nav className="bg-black/30 backdrop-blur-md border border-white/10 rounded-full px-6 py-3">
          <div className="flex justify-between items-center">
            {/* Logo and Brand */}
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-white/10 rounded-lg backdrop-blur-sm">
                <Cloud className="h-4 w-4 text-white" />
              </div>
              <span className="text-base font-semibold text-white tracking-tight">
                Cloud Cost Explorer
              </span>
            </div>

            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center space-x-1">
              <Link href="/">
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-white hover:bg-white/10 hover:text-white px-4 py-2 rounded-full font-medium"
                >
                  Dashboard
                </Button>
              </Link>
              <Link href="/virtual-machines">
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-white/70 hover:bg-white/10 hover:text-white px-4 py-2 rounded-full font-medium"
                >
                  Virtual Machines
                </Button>
              </Link>
              <Link href="/storage">
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-white/70 hover:bg-white/10 hover:text-white px-4 py-2 rounded-full font-medium"
                >
                  Storage
                </Button>
              </Link>
              <Button
                variant="ghost"
                size="sm"
                className="text-white/70 hover:bg-white/10 hover:text-white px-3 py-2 rounded-full font-medium"
              >
                <Settings className="h-4 w-4" />
              </Button>
            </div>

            {/* Right side - Time info */}
            <div className="hidden md:flex items-center space-x-6">
              <div className="text-white/70 text-sm">
                <span className="text-white font-medium text-lg">
                  {currentTime}
                </span>
                <span className="text-white/50 ml-1 text-xs">Time</span>
              </div>
            </div>

            {/* Mobile menu button */}
            <div className="md:hidden">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsMenuOpen(!isMenuOpen)}
                className="text-white hover:bg-white/10 p-2 rounded-full"
              >
                {isMenuOpen ? (
                  <X className="h-5 w-5" />
                ) : (
                  <Menu className="h-5 w-5" />
                )}
              </Button>
            </div>
          </div>
        </nav>
      </div>

      {/* Mobile Navigation Dropdown */}
      {isMenuOpen && (
        <div className="fixed top-20 left-1/2 transform -translate-x-1/2 z-40 w-full max-w-4xl px-4 md:hidden">
          <div className="bg-black/30 backdrop-blur-md border border-white/10 rounded-2xl p-4">
            <div className="space-y-2">
              <Link href="/">
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start text-white hover:bg-white/10 hover:text-white rounded-xl"
                  onClick={() => setIsMenuOpen(false)}
                >
                  <Home className="h-4 w-4 mr-3" />
                  Dashboard
                </Button>
              </Link>
              <Link href="/virtual-machines">
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start text-white/70 hover:bg-white/10 hover:text-white rounded-xl"
                  onClick={() => setIsMenuOpen(false)}
                >
                  <BarChart3 className="h-4 w-4 mr-3" />
                  Virtual Machines
                </Button>
              </Link>
              <Link href="/storage">
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start text-white/70 hover:bg-white/10 hover:text-white rounded-xl"
                  onClick={() => setIsMenuOpen(false)}
                >
                  <BarChart3 className="h-4 w-4 mr-3" />
                  Storage
                </Button>
              </Link>
              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-start text-white/70 hover:bg-white/10 hover:text-white rounded-xl"
              >
                <Settings className="h-4 w-4 mr-3" />
                Settings
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Spacer to prevent content from going under fixed nav */}
      <div className="h-20"></div>
    </>
  );
}
