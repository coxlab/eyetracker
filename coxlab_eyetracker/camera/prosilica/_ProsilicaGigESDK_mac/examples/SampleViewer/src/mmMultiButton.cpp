//
// Name     : mmMultiButton
// Purpose  : A clickable button that can
//            - have a bitmap and/or a text label.
//            - function as a toggle ("on/off") button.
//            - turn active/inactive on entering/leaving it with the mouse.
//            - add a drop-down arrow to the bitmap in a separate section
//              (DROPDOWN) or as part of the bitmap (WHOLEDROPDOWN).
//
//            NOTE:
//            - mmMB_DROPDOWN and mmMB_WHOLEDROPDOWN cannot be used at
//              the same time.
//            - mmMB_STATIC and mmMB_AUTODRAW are mutually exclusive.
//
// Author   : Arne Morken
// Copyright: (C) 2000-2002 MindMatters, www.mindmatters.no
// Licence  : wxWindows licence
//

#include "mmMultiButton.h"

#ifdef __MMDEBUG__
extern wxTextCtrl* gDebug; // For global debug output
#endif

/*
#include "bitmaps/down_btn.xpm"
static wxBitmap gDownBM(down_btn_xpm);
#include "bitmaps/disable.xpm"
static wxBitmap gDisableBM(wxDISABLE_BUTTON_BITMAP);
*/

static wxColour mmDARK_GREY(100,100,100);

IMPLEMENT_DYNAMIC_CLASS(mmMultiButton, wxWindow)

BEGIN_EVENT_TABLE(mmMultiButton,wxWindow)
  EVT_PAINT(mmMultiButton::OnPaint)
  EVT_MOUSE_EVENTS(mmMultiButton::OnMouse)
END_EVENT_TABLE()

bool TileBitmap(const wxRect& rect, wxDC& dc, wxBitmap& bitmap)
{
    int w = bitmap.GetWidth();
    int h = bitmap.GetHeight();
    
    int i, j;
    for (i = rect.x; i < rect.x + rect.width; i += w)
    {
      for (j = rect.y; j < rect.y + rect.height; j+= h)
        dc.DrawBitmap(bitmap, i, j, TRUE);
    }
    return TRUE;
} // TileBitmap

bool mmMultiButton::Create(wxWindow* parent,
		                   const wxWindowID id,
		                   const wxString& label,
                                 wxBitmap& defaultBitmap,
                           const wxPoint& pos,
                           const wxSize& size,
		                   const long int style)
{
  if (!wxWindow::Create(parent, id, pos, size, 0))
    return FALSE;

  if (parent)
    SetBackgroundColour(parent->GetBackgroundColour());
  else
    SetBackgroundColour(*wxLIGHT_GREY);

/*
  if (!gDisableBM.GetMask())
  { // Only set mask for this global bitmap once
    wxMask* mask = new wxMask(gDisableBM,*wxBLACK);
    gDisableBM.SetMask(mask);
  }
  if (!gDownBM.GetMask())
  { // Only set mask for this global bitmap once
    wxMask* mask = new wxMask(gDownBM,GetBackgroundColour());
    gDownBM.SetMask(mask);
  }
  */

  mIsActivated           = FALSE;
  mHasFocus              = FALSE;
  mIsToggleDown          = FALSE;
  mIsWholeDropToggleDown = FALSE;
  mIsDropToggleDown      = FALSE;
  mIsSelected            = FALSE;

  mStyle    = style;
  mLabelStr = label;

  mDefaultBitmap  = &defaultBitmap;
  mFocusBitmap    = mDefaultBitmap;
  mSelectedBitmap = mDefaultBitmap;
  mToggleBitmap   = mDefaultBitmap;

  FindAndSetSize();
  Refresh();

  return TRUE;
} // Constructor

void mmMultiButton::FindAndSetSize()
{
  // Set (total) border size
  if (mStyle & wxBU_AUTODRAW)
    mBorderSize = 3;
  else
  if ((mStyle & wxRAISED_BORDER) || (mStyle & wxSUNKEN_BORDER))
    mBorderSize = 2;
  else
  if (mStyle & wxSIMPLE_BORDER)
    mBorderSize = 2;
  else
    mBorderSize = 0; // Default: No border

  // Set internal margin size (for each side)
  mMarginSize = 2;

  if (!(mStyle & mmMB_NO_AUTOSIZE))
  { // Refresh and set size of button.
    int total_width =0,
        total_height=0;
    if (mDefaultBitmap)
    {
      total_width  = mDefaultBitmap->GetWidth();  // NB! Should use largest bm
      total_height = mDefaultBitmap->GetHeight(); // NB! Should use largest bm
    }
    int labw=0,labh=0,ext=0;
    if (mLabelStr != L"")
      GetTextExtent(mLabelStr,&labw,&labh,&ext);
    labh += ext;
    /*
    if ((mStyle & mmMB_WHOLEDROPDOWN))
      total_width = wxMax(total_width+gDownBM.GetWidth(),labw);
    else */
      total_width = wxMax(total_width,labw);
    total_height += labh;
    /*
    if ((mStyle & mmMB_DROPDOWN))
    {
      total_width += gDownBM.GetWidth();
      total_height = wxMax(total_height,gDownBM.GetHeight());
    }
    */
    int w_extra = mBorderSize + 2*mMarginSize;
    int h_extra = mBorderSize + 2*mMarginSize;
    if (mStyle & mmMB_DROPDOWN)
      w_extra += 2*mMarginSize;
    if (mLabelStr != L"" && mDefaultBitmap)
      h_extra += mMarginSize;
    total_width  += w_extra;
    total_height += h_extra;
#ifdef __MMDEBUG__
    //*gDebug<<"w,h:"<<total_width<<","<<total_height<<"\n";
#endif
    SetSize(total_width,total_height);
    SetAutoLayout(TRUE);
    Layout();
  }
} // FindAndSetSize

void mmMultiButton::OnMouse(wxMouseEvent& event)
// Update button state
{
#ifdef __MMDEBUG__
  //*gDebug<<"mmMultiButton::OnMouse,type:"<<event.GetEventType()<<"\n";
#endif

  mIsActivated = FALSE;

  if ((mStyle & mmMB_STATIC) || !IsEnabled())
  {
    mHasFocus              = FALSE;
    mIsToggleDown          = FALSE;
    mIsWholeDropToggleDown = FALSE;
    mIsDropToggleDown      = FALSE;
    mIsSelected            = FALSE;
    return;
  }

  if (!(mStyle & mmMB_TOGGLE))
    mIsToggleDown          = FALSE;

  if (!(mStyle & mmMB_WHOLEDROPDOWN))
    mIsWholeDropToggleDown = FALSE;

  if (!(mStyle & mmMB_DROPDOWN))
    mIsDropToggleDown      = FALSE;

  bool focus_changed           = FALSE,
       toggle_changed          = FALSE,
       wholedroptoggle_changed = FALSE,
       droptoggle_changed      = FALSE,
       selected_changed        = FALSE;

  int w,h;
  GetClientSize(&w,&h);
  wxPoint mp = event.GetPosition();

  if (event.Entering())
  { // ENTER
    if ((mStyle & mmMB_AUTODRAW) || (mStyle & mmMB_FOCUS))
      focus_changed = !mHasFocus;
    mHasFocus = TRUE;
  }
  else
  if (event.Leaving())
  { // LEAVE
    mIsSelected = FALSE;
    if (!mIsDropToggleDown && !mIsWholeDropToggleDown)
    {
      if ((mStyle & mmMB_AUTODRAW) || (mStyle & mmMB_FOCUS))
        focus_changed = mHasFocus;
      mHasFocus = FALSE;
      if (HasCapture()) ReleaseMouse();
    }
  }
  else
  if (event.LeftDown() || event.LeftDClick())
  { // SELECT
    if (mStyle & mmMB_TOGGLE)
    { // TOGGLE
      if (mIsSelected)
        selected_changed = TRUE;
      mIsSelected = FALSE;
      CaptureMouse();
    }
    else
    if (mStyle & mmMB_WHOLEDROPDOWN)
    { // WHOLEDROPDOWN
      if (MouseIsOnButton())
      {
        if (!mIsSelected)
          selected_changed = TRUE;
        mIsSelected = TRUE;
        wholedroptoggle_changed = TRUE;
        mIsWholeDropToggleDown = !mIsWholeDropToggleDown;
        if (mIsWholeDropToggleDown)
	  CaptureMouse();
        else
          if (HasCapture()) ReleaseMouse();
      }
      else
      { // Pressed outside of button
        if (mIsSelected)
          selected_changed = TRUE;
	mIsSelected = FALSE;
        if (mIsWholeDropToggleDown)
          wholedroptoggle_changed = TRUE;
	mIsWholeDropToggleDown = FALSE;
        if (HasCapture()) ReleaseMouse();
      }
    }
    else
    /*
    if (mStyle & mmMB_DROPDOWN)
    { // DROPDOWN
      if (mp.x > w-gDownBM.GetWidth()-mBorderSize && mp.x < w &&
	      mp.y > mBorderSize && mp.y < h-mBorderSize)
      { // Drop down arrow pressed
        if (mIsSelected)
          selected_changed = TRUE;
	mIsSelected = FALSE;
        droptoggle_changed = TRUE;
        mIsDropToggleDown = !mIsDropToggleDown;
	if (mIsDropToggleDown)
	  CaptureMouse();
        else
          if (HasCapture()) ReleaseMouse();
      }
      else
      if (MouseIsOnButton())
      { // Button (not arrow) pressed
        if (!mIsSelected)
          selected_changed = TRUE;
	mIsSelected = TRUE;
        //if (mIsDropToggleDown)
          //droptoggle_changed = TRUE;
	//mIsDropToggleDown = FALSE;
        CaptureMouse();
      }
      else
      { // Pressed outside of button
        if (mIsSelected)
          selected_changed = TRUE;
	mIsSelected = FALSE;
        if (mIsDropToggleDown)
          droptoggle_changed = TRUE;
	mIsDropToggleDown = FALSE;
        if (HasCapture()) ReleaseMouse();
      }
    }
    else
    */
    { // 'Normal' button
      if (!mIsSelected)
        selected_changed = TRUE;
      mIsSelected = TRUE;
      CaptureMouse();
    }
    if (!MouseIsOnButton())
    {
      focus_changed = mHasFocus;
      mHasFocus = FALSE;
    }
  }
  else
  if (event.LeftUp())
  { // ACTIVATE
    if (mStyle & mmMB_TOGGLE)
    { // TOGGLE
      if (mIsSelected)
        selected_changed = TRUE;
      mIsSelected = FALSE;
      toggle_changed = TRUE;
      mIsToggleDown = !mIsToggleDown;
      if (HasCapture()) ReleaseMouse();
    }
    else
    if (mStyle & mmMB_WHOLEDROPDOWN)
    { // WHOLEDROPDOWN
      if (mIsSelected)
        selected_changed = TRUE;
      mIsSelected = FALSE;
      if (!mIsWholeDropToggleDown)
        if (HasCapture()) ReleaseMouse();
    }
    /*
    else
    if (mStyle & mmMB_DROPDOWN)
    { // DROPDOWN
      if (mIsSelected)
        selected_changed = TRUE;
      mIsSelected = FALSE;
      if (mp.x > w-gDownBM.GetWidth()-mBorderSize && mp.x < w &&
	      mp.y > mBorderSize && mp.y < h-mBorderSize)
      { // Drop down arrow pressed
        if (!mIsDropToggleDown)
          if (HasCapture()) ReleaseMouse();
      }
      else
      if (MouseIsOnButton())
      { // Button (not arrow) pressed
        if (mIsDropToggleDown)
          droptoggle_changed = TRUE;
	mIsDropToggleDown = FALSE;
	if (!droptoggle_changed)
          mIsActivated = TRUE; // NOTE! SEND ACTIVATE SIGNAL!
        if (HasCapture()) ReleaseMouse();
      }
    }
    */
    else
    { // 'Normal' button
      if (mIsSelected)
        selected_changed = TRUE;
      mIsSelected = FALSE;
      mIsActivated = TRUE; // NOTE! SEND ACTIVATE SIGNAL!
      if (HasCapture()) ReleaseMouse();
    }
  }

  // Redraw only if neccessary
  if (focus_changed || selected_changed || wholedroptoggle_changed || droptoggle_changed || toggle_changed)
  {
    Refresh();
    // Generate events to let derived class know what happened
    if (focus_changed)
    { // ENTER/LEAVE
      wxCommandEvent ev(event.GetEventType(),GetId());
      if (mHasFocus)
        ev.SetEventType(wxEVT_ENTER_WINDOW);
      else
        ev.SetEventType(wxEVT_LEAVE_WINDOW);
      GetEventHandler()->ProcessEvent(ev); // Neccessary?
    }
    if (toggle_changed)
    { // TOGGLE
      wxCommandEvent ev(mmEVT_TOGGLE,GetId());
      GetEventHandler()->ProcessEvent(ev);
    }
    if (wholedroptoggle_changed)
    { // WHOLEDROPDOWN
      wxCommandEvent ev(mmEVT_WHOLEDROP_TOGGLE,GetId());
      GetEventHandler()->ProcessEvent(ev);
    }
    if (droptoggle_changed)
    { // DROPDOWN
      wxCommandEvent ev(mmEVT_DROP_TOGGLE,GetId());
      GetEventHandler()->ProcessEvent(ev);
    }
    if (selected_changed)
    { // SELECT
      wxCommandEvent ev(wxEVT_COMMAND_LEFT_CLICK,GetId());
      GetEventHandler()->ProcessEvent(ev);
    }
    if (mIsActivated)
    { // ACTIVATE
      wxCommandEvent ev(wxEVT_COMMAND_BUTTON_CLICKED,GetId());
      GetEventHandler()->ProcessEvent(ev);
    }
  } // if
  event.Skip();
} // OnMouse

void mmMultiButton::OnPaint(wxPaintEvent& event)
{
  wxPaintDC dc(this);
  dc.SetBackground(*wxTheBrushList->FindOrCreateBrush(GetBackgroundColour(),wxSOLID));
  dc.Clear();
  RedrawBitmaps(dc);
  RedrawLabel(dc);
  RedrawBorders(dc);
} // OnPaint

void mmMultiButton::RedrawBitmaps(wxDC& dc)
// Redraw icons
{
  // Find the current bitmap
  wxBitmap* bm = mDefaultBitmap; // Default bitmap
  if ((mStyle & mmMB_FOCUS) && mHasFocus)
    bm = mFocusBitmap; // Focused bitmap
  if ((mStyle & mmMB_SELECT) && mIsSelected)
    bm = mSelectedBitmap; // Selected bitmap
  if ((mStyle & mmMB_TOGGLE) && mIsToggleDown)
    bm = mToggleBitmap; // Toggle bitmap

  int w,h;
  GetClientSize(&w,&h);

  int offset = 0;
  if (mStyle & mmMB_AUTODRAW)
    if (((mHasFocus && mIsSelected) || mIsToggleDown || mIsWholeDropToggleDown) && !mIsDropToggleDown)
      offset = 1;

  // Draw the bitmap
  int lw=0,lh=0,ext=0;
  if (mLabelStr != L"")
    GetTextExtent(mLabelStr,&lw,&lh,&ext);
  lh += ext;
  int bmdown_x_off = 0;
  /*
  if ((mStyle & mmMB_WHOLEDROPDOWN) || (mStyle & mmMB_DROPDOWN))
    bmdown_x_off = gDownBM.GetWidth();
    */
  int x_off = bm->GetWidth()  + bmdown_x_off;
  int y_off = bm->GetHeight() + lh;
  int x = offset + wxMax(int((w-x_off)/2),int((lw-x_off)/2));
  int y = offset + int((h-y_off)/2);
  if (bm && bm->Ok())
  {
    if (IsEnabled())
      dc.DrawBitmap(*bm,x,y,TRUE);
    else
    {
      dc.DrawBitmap(*bm,x,y,TRUE);
      wxRect rect(0, 0, GetClientSize().x, GetClientSize().y);
      //TileBitmap(rect,dc,gDisableBM);
    }
  }

/*
  // Draw the drop-down-arrow
  if (((mStyle & mmMB_DROPDOWN) || (mStyle & mmMB_WHOLEDROPDOWN)))
  {
    if (mIsDropToggleDown)
      offset = 1;
    int x_off = gDownBM.GetWidth();
    int y_off = gDownBM.GetHeight();
    int x = offset + w-x_off;
    int y = offset + int((h-y_off)/2);
    dc.DrawBitmap(gDownBM,x,y,TRUE);
  }
  */
} // RedrawBitmaps

void mmMultiButton::RedrawLabel(wxDC& dc)
// Redraw label
{
  int w,h;
  GetClientSize(&w,&h);
 
  int offset = 0;
  if (mStyle & mmMB_AUTODRAW)
    if (((mHasFocus && mIsSelected) || mIsToggleDown || mIsWholeDropToggleDown) && !mIsDropToggleDown)
      offset = 1;

  int lw=0,lh=0,ext=0;
  GetTextExtent(mLabelStr,&lw,&lh,&ext);
  lh += ext;

  int bmdown_off = 0;
  /*
  if (mStyle & mmMB_DROPDOWN)
    bmdown_off = gDownBM.GetWidth();
  */
  int x_off = lw + bmdown_off;
  int y_off = lh + mMarginSize;
  int x = offset + wxMax(int((w-x_off)/2),int((lw-x_off)/2)) - 1;
  int y = offset + wxMax(h-y_off,0);

  dc.SetFont(GetFont());
  if (IsEnabled())
  {
    dc.SetTextForeground(GetForegroundColour());
    dc.DrawText(mLabelStr, x,y);
  }
  else
  {
    dc.SetTextForeground(*wxWHITE);
    dc.DrawText(mLabelStr, x+1,y+1);
    dc.SetTextForeground(mmDARK_GREY);
    dc.DrawText(mLabelStr, x,y);
    dc.SetTextForeground(*wxBLACK);
  }
} // RedrawLabel

void mmMultiButton::RedrawBorders(wxDC& dc)
// Draw all borders of the button.
{
  if ((mStyle & wxBU_AUTODRAW) ||
      // Don't draw borders if wxBitmapButton does it.
      ((mStyle & mmMB_AUTODRAW) && !mHasFocus) ||
      // If mmMB_AUTODRAW, borders are only drawn if button has focus.
      (!(mStyle & mmMB_AUTODRAW) && (mStyle & wxNO_BORDER)))
      // If not mmMB_AUTODRAW and no border, there's nothing to do.
    return;

  int w,h;
  GetClientSize(&w,&h);

/*
  if (mStyle & mmMB_DROPDOWN)
    w -= gDownBM.GetWidth();
    */

  if (mStyle & wxSIMPLE_BORDER)
  {
    dc.SetPen(*wxThePenList->FindOrCreatePen(*wxBLACK, 1,wxSOLID));
    dc.DrawLine(0,0,0,h-1);
    dc.DrawLine(0,0,w,0);
    dc.DrawLine(0,h-1,w,h-1);
    dc.DrawLine(w-1,0,w-1,h-1);
    // Drop-down arrow
    /*
    if (mStyle & mmMB_DROPDOWN)
    {
      w += gDownBM.GetWidth();
      int x = w-gDownBM.GetWidth()-1;
      dc.SetPen(*wxThePenList->FindOrCreatePen(*wxBLACK, 1,wxSOLID));
      dc.DrawLine(x,0,x,h-1);
      dc.DrawLine(x,0,w,0);
      dc.DrawLine(x,h-1,w,h-1);
      dc.DrawLine(w-1,0,w-1,h-1);
    }
    */
  }
  else
  if (((mStyle & wxSUNKEN_BORDER) &&
      !(mIsSelected || mIsToggleDown || mIsWholeDropToggleDown) && !mIsDropToggleDown) ||
      ((mStyle & wxRAISED_BORDER) &&
       (mIsSelected || mIsToggleDown || mIsWholeDropToggleDown) && !mIsDropToggleDown) ||
      (!(mStyle & wxSUNKEN_BORDER) &&
       (mIsSelected || mIsToggleDown || mIsWholeDropToggleDown) && !mIsDropToggleDown))
  { // Has focus, and is selected or toggled down
    dc.SetPen(*wxWHITE_PEN);
    dc.DrawLine(0,  h-1,w-1,h-1);
    dc.DrawLine(w-1,0,  w-1,h);
    dc.SetPen(*wxThePenList->FindOrCreatePen(*wxBLACK, 1,wxSOLID));
    dc.DrawLine(0,0,0,h);
    dc.DrawLine(0,0,w,0);
    // Drop-down arrow
    /*
    if (mStyle & mmMB_DROPDOWN)
    {
      w += gDownBM.GetWidth();
      int x = w-gDownBM.GetWidth();
      dc.SetPen(*wxWHITE_PEN);
      dc.DrawLine(x,  h-1,w-1,h-1);
      dc.DrawLine(w-1,0,  w-1,h);
      dc.SetPen(*wxThePenList->FindOrCreatePen(*wxBLACK, 1,wxSOLID));
      dc.DrawLine(x,0,x,h);
      dc.DrawLine(x,0,w,0);
    }
    */
  }
  else
  { // Has focus, not selected or toggled down
    dc.SetPen(*wxWHITE_PEN);
    dc.DrawLine(0,0,0,  h-1);
    dc.DrawLine(0,0,w-1,0);
    dc.SetPen(*wxThePenList->FindOrCreatePen(*wxBLACK, 1,wxSOLID));
    dc.DrawLine(0,  h-1,w-1,h-1);
    dc.DrawLine(w-1,0,  w-1,h);
    // Drop-down arrow
    /*
    if (mStyle & mmMB_DROPDOWN)
    {
      w += gDownBM.GetWidth();
      int x = w-gDownBM.GetWidth();
      if (!mIsDropToggleDown)
        dc.SetPen(*wxWHITE_PEN);
      else
        dc.SetPen(*wxThePenList->FindOrCreatePen(*wxBLACK, 1,wxSOLID));
      dc.DrawLine(x,  0,  x,  h-1);
      dc.DrawLine(x,  0,  w-1,0);
      if (mIsDropToggleDown)
        dc.SetPen(*wxWHITE_PEN);
      else
        dc.SetPen(*wxThePenList->FindOrCreatePen(*wxBLACK, 1,wxSOLID));
      dc.DrawLine(x,  h-1,w-1,h-1);
      dc.DrawLine(w-1,0,  w-1,h);
    }
    */
  }
} // RedrawBorders

void mmMultiButton::SetDefaultBitmap(wxBitmap& bm)
{
  mDefaultBitmap = &bm;
  Refresh();
} // SetDefaultBitmap

void mmMultiButton::SetFocusBitmap(wxBitmap& bm)
{
  mFocusBitmap = &bm;
  if (!mDefaultBitmap)
    mDefaultBitmap = &bm;
  Refresh();
} // SetFocusBitmap

void mmMultiButton::SetSelectedBitmap(wxBitmap& bm)
{
  mSelectedBitmap = &bm;
  if (!mDefaultBitmap)
    mDefaultBitmap = &bm;
  Refresh();
} // SetSelectedBitmap

void mmMultiButton::SetToggleBitmap(wxBitmap& bm)
{
  mToggleBitmap = &bm;
  if (!mDefaultBitmap)
    mDefaultBitmap = &bm;
  Refresh();
} // SetToggleBitmap

void mmMultiButton::SetLabel(wxString label)
// Sets the string label.
{
  mLabelStr = label;
  Refresh();
} // SetLabel

void mmMultiButton::SetStyle(const long style)
{
  mStyle = style;
  Refresh();
} // SetStyle

void mmMultiButton::SetFocus(const bool hasFocus)
// Update button state.
{
  mHasFocus = hasFocus;
  Refresh();
} // SetSelected

void mmMultiButton::SetSelected(const bool isSelected)
// Update button state.
{
  mIsSelected = isSelected;
  Refresh();
} // SetSelected

void mmMultiButton::SetToggleDown(const bool isToggleDown)
// Update button state.
{
  mIsToggleDown = isToggleDown;
  Refresh();
} // SetToggleDown

void mmMultiButton::SetWholeDropToggleDown(const bool isWholeDropToggleDown)
// Update button state.
{
  mIsWholeDropToggleDown = isWholeDropToggleDown;
  Refresh();
} // SetWholeDropToggleDown

void mmMultiButton::SetDropToggleDown(const bool isDropToggleDown)
// Update button state.
{
  mIsDropToggleDown = isDropToggleDown;
  Refresh();
} // SetDropToggleDown

bool mmMultiButton::MouseIsOnButton()
{
  int cx=0,cy=0;
  ClientToScreen(&cx,&cy);
  int cw=0,ch=0;
  GetClientSize(&cw,&ch);
  int mpx,mpy;
  ::wxGetMousePosition(&mpx,&mpy);
  return(mpx >= cx && mpx <= cx + cw &&
         mpy >= cy && mpy <= cy + ch);
} // MouseIsOnButton

bool mmMultiButton::Enable(bool enable)
{
  bool ret = wxWindowBase::Enable(enable);
  Refresh();
  return ret;
} // Enable
