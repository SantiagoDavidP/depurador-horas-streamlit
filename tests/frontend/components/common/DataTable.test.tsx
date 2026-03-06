import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { DataTable } from '@/components/common/DataTable'

describe('DataTable', () => {
  const mockColumns = [
    { key: 'id', label: 'ID', sortable: true },
    { key: 'name', label: 'Name', sortable: true },
    { key: 'email', label: 'Email', sortable: false },
  ]

  const mockData = [
    { id: 1, name: 'John Doe', email: 'john@example.com' },
    { id: 2, name: 'Jane Smith', email: 'jane@example.com' },
    { id: 3, name: 'Bob Johnson', email: 'bob@example.com' },
  ]

  it('renders_table_with_columns_and_data', () => {
    render(<DataTable columns={mockColumns} data={mockData} />)

    // Check headers
    expect(screen.getByText('ID')).toBeInTheDocument()
    expect(screen.getByText('Name')).toBeInTheDocument()
    expect(screen.getByText('Email')).toBeInTheDocument()

    // Check data
    expect(screen.getByText('John Doe')).toBeInTheDocument()
    expect(screen.getByText('jane@example.com')).toBeInTheDocument()
  })

  it('shows_empty_state_when_no_data', () => {
    render(<DataTable columns={mockColumns} data={[]} />)
    expect(screen.getByText(/no hay datos disponibles/i)).toBeInTheDocument()
  })

  it('renders_custom_empty_message', () => {
    render(
      <DataTable
        columns={mockColumns}
        data={[]}
        emptyMessage="No records found"
      />
    )
    expect(screen.getByText('No records found')).toBeInTheDocument()
  })

  it('calls_onRowClick_when_row_is_clicked', async () => {
    const handleRowClick = vi.fn()
    const user = userEvent.setup()

    render(
      <DataTable
        columns={mockColumns}
        data={mockData}
        onRowClick={handleRowClick}
      />
    )

    const firstRow = screen.getByText('John Doe').closest('tr')
    await user.click(firstRow!)

    expect(handleRowClick).toHaveBeenCalledWith(mockData[0])
  })

  it('applies_hover_effect_when_rows_are_clickable', () => {
    render(
      <DataTable
        columns={mockColumns}
        data={mockData}
        onRowClick={() => {}}
      />
    )

    const firstRow = screen.getByText('John Doe').closest('tr')
    expect(firstRow).toHaveClass('hover:bg-gray-50', 'cursor-pointer')
  })

  it('sorts_data_when_sortable_column_header_clicked', async () => {
    const user = userEvent.setup()

    render(<DataTable columns={mockColumns} data={mockData} />)

    const nameHeader = screen.getByText('Name')
    await user.click(nameHeader)

    // Should sort ascending
    const rows = screen.getAllByRole('row')
    const firstDataRow = rows[1] // Skip header row
    expect(within(firstDataRow).getByText('Bob Johnson')).toBeInTheDocument()

    // Click again to sort descending
    await user.click(nameHeader)
    const rowsDesc = screen.getAllByRole('row')
    const firstDataRowDesc = rowsDesc[1]
    expect(within(firstDataRowDesc).getByText('John Doe')).toBeInTheDocument()
  })

  it('does_not_sort_when_non_sortable_column_clicked', async () => {
    const user = userEvent.setup()

    render(<DataTable columns={mockColumns} data={mockData} />)

    const emailHeader = screen.getByText('Email')
    await user.click(emailHeader)

    // Data order should remain unchanged
    const rows = screen.getAllByRole('row')
    const firstDataRow = rows[1]
    expect(within(firstDataRow).getByText('John Doe')).toBeInTheDocument()
  })

  it('shows_loading_state', () => {
    render(<DataTable columns={mockColumns} data={mockData} loading />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('renders_with_pagination', () => {
    const pagination = {
      page: 1,
      pageSize: 10,
      total: 100,
      onPageChange: vi.fn(),
    }

    render(
      <DataTable columns={mockColumns} data={mockData} pagination={pagination} />
    )

    expect(screen.getByText(/página 1/i)).toBeInTheDocument()
    expect(screen.getByText(/100/i)).toBeInTheDocument()
  })

  it('calls_onPageChange_when_pagination_button_clicked', async () => {
    const handlePageChange = vi.fn()
    const user = userEvent.setup()

    const pagination = {
      page: 1,
      pageSize: 10,
      total: 100,
      onPageChange: handlePageChange,
    }

    render(
      <DataTable columns={mockColumns} data={mockData} pagination={pagination} />
    )

    const nextButton = screen.getByRole('button', { name: /siguiente/i })
    await user.click(nextButton)

    expect(handlePageChange).toHaveBeenCalledWith(2)
  })

  it('renders_custom_cell_content', () => {
    const customColumns = [
      {
        key: 'id',
        label: 'ID',
        render: (value: number) => <strong>#{value}</strong>,
      },
      { key: 'name', label: 'Name' },
    ]

    render(<DataTable columns={customColumns} data={mockData} />)

    expect(screen.getByText('#1')).toBeInTheDocument()
    expect(screen.getByText('#2')).toBeInTheDocument()
  })

  it('applies_custom_className', () => {
    const { container } = render(
      <DataTable columns={mockColumns} data={mockData} className="custom-table" />
    )

    expect(container.querySelector('.custom-table')).toBeInTheDocument()
  })

  it('renders_with_striped_rows', () => {
    render(<DataTable columns={mockColumns} data={mockData} striped />)

    const rows = screen.getAllByRole('row')
    const evenRow = rows[2] // First data row (index 1) is odd in table
    expect(evenRow).toHaveClass('bg-gray-50')
  })

  it('renders_with_selection_checkboxes', () => {
    render(<DataTable columns={mockColumns} data={mockData} selectable />)

    const checkboxes = screen.getAllByRole('checkbox')
    // Should have header checkbox + one per row
    expect(checkboxes).toHaveLength(mockData.length + 1)
  })

  it('selects_row_when_checkbox_clicked', async () => {
    const handleSelectionChange = vi.fn()
    const user = userEvent.setup()

    render(
      <DataTable
        columns={mockColumns}
        data={mockData}
        selectable
        onSelectionChange={handleSelectionChange}
      />
    )

    const checkboxes = screen.getAllByRole('checkbox')
    await user.click(checkboxes[1]) // First data row checkbox

    expect(handleSelectionChange).toHaveBeenCalledWith([mockData[0]])
  })

  it('selects_all_rows_when_header_checkbox_clicked', async () => {
    const handleSelectionChange = vi.fn()
    const user = userEvent.setup()

    render(
      <DataTable
        columns={mockColumns}
        data={mockData}
        selectable
        onSelectionChange={handleSelectionChange}
      />
    )

    const headerCheckbox = screen.getAllByRole('checkbox')[0]
    await user.click(headerCheckbox)

    expect(handleSelectionChange).toHaveBeenCalledWith(mockData)
  })
})
