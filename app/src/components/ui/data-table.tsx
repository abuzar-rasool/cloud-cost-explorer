"use client";

import React, { useState } from "react";
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
  getSortedRowModel,
  SortingState,
  getFilteredRowModel,
  ColumnFiltersState,
} from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ChevronDown, ChevronUp, ChevronsUpDown, Search } from "lucide-react";

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  searchKey?: string;
  searchPlaceholder?: string;
  pagination?: {
    pageIndex: number;
    pageSize: number;
    pageCount: number;
    totalCount: number;
    hasNextPage: boolean;
    hasPrevPage: boolean;
    onPageChange: (page: number) => void;
    onPageSizeChange: (size: number) => void;
  };
  sorting?: {
    sortBy: string;
    sortOrder: "asc" | "desc";
    onSortingChange: (sortBy: string, sortOrder: "asc" | "desc") => void;
  };
}

export function DataTable<TData, TValue>({
  columns,
  data,
  searchPlaceholder = "Search...",
  pagination,
  sorting,
}: DataTableProps<TData, TValue>) {
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = useState("");

  // Initialize sorting state from props
  const [sortingState, setSortingState] = useState<SortingState>(
    sorting ? [{ id: sorting.sortBy, desc: sorting.sortOrder === "desc" }] : []
  );

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    // Disable built-in sorting when using server-side sorting
    ...(sorting ? {} : { getSortedRowModel: getSortedRowModel() }),
    getFilteredRowModel: getFilteredRowModel(),
    // Disable TanStack Table's built-in pagination since we're using custom pagination
    // getPaginationRowModel: getPaginationRowModel(),
    onSortingChange: (updater) => {
      const newSorting = typeof updater === 'function' ? updater(sortingState) : updater;
      setSortingState(newSorting);
      
      // Call the API sorting handler if provided
      if (sorting && newSorting.length > 0) {
        const sortItem = newSorting[0];
        sorting.onSortingChange(sortItem.id, sortItem.desc ? "desc" : "asc");
      } else if (sorting) {
        // Reset to default sorting
        sorting.onSortingChange("price_per_hour_usd", "asc");
      }
    },
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    globalFilterFn: "includesString",
    state: {
      sorting: sortingState,
      columnFilters,
      globalFilter,
    },
  });

  const getSortIcon = (column: {
    getCanSort: () => boolean;
    getIsSorted: () => string | false;
  }) => {
    if (!column.getCanSort()) return null;

    if (column.getIsSorted() === "asc") {
      return <ChevronUp className="h-4 w-4" />;
    }
    if (column.getIsSorted() === "desc") {
      return <ChevronDown className="h-4 w-4" />;
    }
    return <ChevronsUpDown className="h-4 w-4" />;
  };

  return (
    <div className="space-y-4">
      {/* Search and Filters */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder={searchPlaceholder}
              value={globalFilter ?? ""}
              onChange={(event) => setGlobalFilter(event.target.value)}
              className="pl-8 w-[300px] bg-input border-border text-foreground placeholder:text-muted-foreground hover:bg-accent focus:bg-accent"
            />
          </div>
        </div>

        {pagination && (
          <div className="flex items-center space-x-2 text-sm text-muted-foreground">
            <span>
              Showing {pagination.pageIndex * pagination.pageSize + 1} to{" "}
              {Math.min(
                (pagination.pageIndex + 1) * pagination.pageSize,
                pagination.totalCount
              )}{" "}
              of {pagination.totalCount} results
            </span>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="rounded-md border border-border bg-card backdrop-blur-sm">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow
                key={headerGroup.id}
                className="border-border hover:bg-accent"
              >
                {headerGroup.headers.map((header) => (
                  <TableHead
                    key={header.id}
                    className="bg-accent border-border"
                  >
                    {header.isPlaceholder ? null : (
                      <div
                        className={`flex items-center space-x-1 text-foreground ${
                          header.column.getCanSort()
                            ? "cursor-pointer select-none hover:text-muted-foreground"
                            : ""
                        }`}
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                        {getSortIcon(header.column)}
                      </div>
                    )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && "selected"}
                  className="border-border hover:bg-accent transition-colors"
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id} className="border-border">
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-24 text-center text-muted-foreground"
                >
                  No results found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {pagination && (
        <div className="flex items-center justify-between space-x-2 py-4">
          <div className="flex-1 text-sm text-muted-foreground">
            Showing {pagination.pageIndex * pagination.pageSize + 1} to{" "}
            {Math.min(
              (pagination.pageIndex + 1) * pagination.pageSize,
              pagination.totalCount
            )}{" "}
            of {pagination.totalCount} results
          </div>
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => pagination.onPageChange(Math.max(0, pagination.pageIndex - 1))}
              disabled={!pagination.hasPrevPage || pagination.pageIndex <= 0}
              className="text-foreground border-border hover:bg-accent disabled:opacity-50"
            >
              Previous
            </Button>

            {/* Page numbers */}
            <div className="flex items-center space-x-1">
              {/* First page */}
              {pagination.pageIndex > 2 && pagination.pageCount > 1 && (
                <>
                  <Button
                    variant={pagination.pageIndex === 0 ? "default" : "outline"}
                    size="sm"
                    onClick={() => pagination.onPageChange(0)}
                  >
                    1
                  </Button>
                  {pagination.pageIndex > 3 && (
                    <span className="px-2 text-muted-foreground">...</span>
                  )}
                </>
              )}

              {/* Current page and surrounding pages */}
              {Array.from(
                { length: Math.min(5, pagination.pageCount) },
                (_, i) => {
                  const pageNum = Math.max(0, pagination.pageIndex - 2) + i;
                  if (pageNum >= pagination.pageCount) return null;

                  return (
                    <Button
                      key={pageNum}
                      variant={
                        pageNum === pagination.pageIndex ? "default" : "outline"
                      }
                      size="sm"
                      onClick={() => pagination.onPageChange(pageNum)}
                    >
                      {pageNum + 1}
                    </Button>
                  );
                }
              ).filter(Boolean)}

              {/* Last page */}
              {pagination.pageIndex < pagination.pageCount - 3 &&
                pagination.pageCount > 1 && (
                  <>
                    {pagination.pageIndex < pagination.pageCount - 4 && (
                      <span className="px-2 text-muted-foreground">...</span>
                    )}
                    <Button
                      variant={
                        pagination.pageIndex === pagination.pageCount - 1
                          ? "default"
                          : "outline"
                      }
                      size="sm"
                      onClick={() =>
                        pagination.onPageChange(
                          Math.max(0, pagination.pageCount - 1)
                        )
                      }
                    >
                      {pagination.pageCount}
                    </Button>
                  </>
                )}
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => pagination.onPageChange(Math.min(pagination.pageCount - 1, pagination.pageIndex + 1))}
              disabled={!pagination.hasNextPage || pagination.pageIndex >= pagination.pageCount - 1}
              className="text-foreground border-border hover:bg-accent disabled:opacity-50"
            >
              Next
            </Button>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-sm text-muted-foreground">
              Rows per page:
            </span>
            <select
              value={pagination.pageSize}
              onChange={(e) =>
                pagination.onPageSizeChange(Number(e.target.value))
              }
              className="border border-border rounded px-3 py-1.5 text-sm bg-input text-foreground hover:bg-accent focus:bg-accent focus:outline-none focus:ring-2 focus:ring-ring"
              style={{
                colorScheme: "dark",
              }}
            >
              {[10, 25, 50, 100].map((size) => (
                <option
                  key={size}
                  value={size}
                  className="bg-popover text-foreground"
                >
                  {size}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}
    </div>
  );
}
